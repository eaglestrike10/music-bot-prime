import discord
from discord.ext import commands, tasks
import asyncio
import os

DISCORD_TOKEN = os.getenv("discord_token")

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!', intents=intents)

ffmpeg_options = {
    'options': '-vn'
}

music_queue = []


@bot.command(name='join', help='Tells the bot to join the voice channel')
async def join(ctx):
    play_track.start(ctx)
    if not ctx.message.author.voice:
        await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
        return
    else:
        channel = ctx.message.author.voice.channel
    await channel.connect()


@bot.command(name='leave', help='To make the bot leave the voice channel')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("The bot is not connected to a voice channel.")


@bot.command(name='play', help='To play song')
async def play(ctx, music_track):
    try:
        async with ctx.typing():
            music_queue.append(music_track)
        await ctx.send('**Added to queue:** {}'.format(music_track))
    except:
        await ctx.send("There was an error playing the track")


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


@bot.command(name='stop', help='Stops playing and clears the queue')
async def stop(ctx):
    global music_queue
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        music_queue = []
        await voice_client.stop()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


@bot.command(name='list', help='Returns a list of all tracks in library')
async def list_tracks(ctx):
    song_list = os.listdir("music")
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


@tasks.loop(seconds=5)
async def play_track(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client
    while len(music_queue) > 0:
        music_track = "music/{}".format(music_queue.pop(0))
        if not os.path.exists(music_track):
            await ctx.send("Does not exist: {}".format(music_track))
        voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=music_track))
        while voice_channel.is_playing():
            await asyncio.sleep(3)


def format_song_list(song_list, message_header="Here's a list"):
    message = "{} \n```\n".format(message_header)
    for s in song_list:
        message += (s + '\n')
    message += "\n```"

    return message


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
