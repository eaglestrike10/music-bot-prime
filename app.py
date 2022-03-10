from discord.ext import commands, tasks
import discord
import asyncio
import requests
import os

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!', intents=intents)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
file_formats = ["audio/mpeg", "video/webm"]
music_lib_dir = "music"
music_queue = []


@bot.command(name='play', help='To play song')
async def play(ctx, music_track):
    voice_client = ctx.message.guild.voice_client
    async with ctx.typing():
        if not play_track.is_running():
            play_track.start(ctx)
        if not voice_client:   #check if user issuing command is connected to a channel
            if not ctx.message.author.voice:    #if not, write error
                await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
                return
            else:   #attempt connection to voice channel
                channel = ctx.message.author.voice.channel
            await channel.connect()

    music_queue.append(music_track)
    await ctx.send('**Added to queue:** {}'.format(music_track))


@bot.command(name='pause', help='This command pauses the song')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


@bot.command(name='resume', help='Resumes the song')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        await voice_client.resume()
    else:
        await ctx.send("The bot was not playing anything before this. Use play command")


@bot.command(name='skip', help='Skips the current song')
async def skip(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.stop()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


@bot.command(name='stop', help='Stops playing, clears the queue, and disconnect the bot')
async def stop(ctx):
    global music_queue
    voice_client = ctx.message.guild.voice_client
    await voice_client.disconnect()  # disconnect
    music_queue = []
    # await voice_client.stop()

    # if voice_client: #if connected to voice channel
    #     if voice_client.is_playing():   #if there is a queue, clear queue and stop music
    # else:   #if not connected to voice channel
    #     await ctx.send("The bot is not playing anything at the moment.")


@bot.command(name='list', help='Returns a list of all tracks in library')
async def list_tracks(ctx):
    song_list = os.listdir(music_lib_dir)
    message_header = "Here's a list of all tracks on the system:"
    await ctx.send(format_song_list(song_list, message_header))


@bot.command(name='queue', help='Returns the current queue')
async def queue(ctx):
    global music_queue
    if not music_queue:
        await ctx.send("Queue is currently empty")
        return
    message_header = "Current queue:"
    await ctx.send(format_song_list(music_queue, message_header))


@bot.command(name='add', help='Adds song to library')
async def add(ctx):  # triggers when a message is sent
    if ctx.message.attachments:  # if message has an attached file or image
        for attachment in ctx.message.attachments:
            if attachment.content_type in file_formats:  # check attachment type
                if attachment.filename not in os.listdir(music_lib_dir):  # check if file already exists
                    r = requests.get(attachment.url, allow_redirects=True)  # if not, download file from url
                    # write contents of download request to folder
                    open(os.path.join(music_lib_dir, attachment.filename), 'wb').write(r.content)
                    await ctx.send("Added track: ".format(attachment.filename))
                else:
                    await ctx.send("Track is already in library: {}".format(attachment.filename))
            else:
                await ctx.send("Unsupported file format {}".format(attachment.content_type))


@tasks.loop(seconds=5)
async def play_track(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client
    while len(music_queue) > 0:
        music_track = music_queue[0]
        music_path = os.path.join(music_lib_dir, music_track)
        if not os.path.exists(music_path):
            await ctx.send("**Does not exist:** {}".format(music_track))
        voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=music_path))
        await ctx.send("**Now Playing:** {}".format(music_track))
        while voice_channel.is_playing():
            await asyncio.sleep(3)
        # Handle a queue clear while playing a track
        if music_queue:
            music_queue.pop(0)


def format_song_list(song_list, message_header="Here's a list"):
    message = "{} \n```\n".format(message_header)
    for s in song_list:
        message += (s + '\n')
    message += "\n```"

    return message


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
