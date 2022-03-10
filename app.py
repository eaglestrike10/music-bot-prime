import discord
from discord.ext import commands, tasks
import subprocess
import asyncio
import requests
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


@bot.command(name='stop', help='Stops the song')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.stop()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


@bot.command(name='list', help='Returns a list of all tracks in library')
async def stop(ctx):
    song_list = "Here's a list of all tracks \n```\n"

    for s in os.listdir("music"):
        song_list += ("music/{}\n".format(s))
    song_list += "\n```"

    await ctx.send(song_list)


@tasks.loop(seconds=5)
async def play_track(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client
    while len(music_queue) > 0:
        music_track = music_queue.pop(0)
        voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=music_track))
        await asyncio.sleep(get_music_length(music_track))


def get_music_length(music_track):
    args = ["ffprobe", "-show_entries", "format=duration", "-i", music_track]
    popen = subprocess.Popen(args, stdout=subprocess.PIPE)
    popen.wait()
    ret = popen.stdout.read().decode("utf-8")                   # ffprobe return
    duration = float(ret.split('duration=')[1].split("\n")[0])  # Formatting return

    return duration + 5                                         # Return with 5 seconds of margin


@client.event
async def on_message(msg):   #triggers when a message is sent
    if msg.author == client.user:   #prevent recursion if sender is bot
        return
    elif msg.attachments:   #if message has an attached file or image
        for attachment in msg.attachments:
            if attachment.content_type == "mp3":
                if not attachment.filename in os.listdir("music"):
                    r = requests.get(attachment.url, allow_redirects=True)
                    open(attachment.filename, 'wb').write(r.content)
            



if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)