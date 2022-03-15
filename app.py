from discord.ext import commands, tasks
import requests
import discord
import asyncio
import random
import os
from fuzzywuzzy import process    #more comprehensive string comparison library

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!', intents=intents)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
file_formats = ["audio/mpeg", "video/webm"]
track_lib_dir = "music"
track_list_file = "track_list.txt"
track_queue = []


@bot.command(name='play', help='Plays a track specified by user')
async def play(ctx, *args):
    voice_client = ctx.message.guild.voice_client
    async with ctx.typing():
        if not voice_client:  # check if user issuing command is connected to a channel
            if not ctx.message.author.voice:  # if not, write error
                await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
                return
            else:  # attempt connection to voice channel
                channel = ctx.message.author.voice.channel
            await channel.connect()

    if args:
        track_name = "".join(args)
        track_name = keyword_search(track_name)
        await ctx.send("**Closest match:** {}".format(track_name))
        if track_name:
            track_queue.append(track_name)
            await ctx.send('**Added to queue:** {}'.format(track_name))
        else:
            await ctx.send("**Does not exist:** {}".format(track_name))
        if not play_track.is_running():
            play_track.start(track_name)


@bot.command(name='pause', help='This command pauses the track')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


@bot.command(name='resume', help='Resumes playing')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        voice_client.resume()
    else:
        await ctx.send("The bot was not playing anything before this. Use play command")


@bot.command(name='skip', help='Skips the current track')
async def skip(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


@bot.command(name='stop', help='Stops playing, clears the queue, and disconnect the bot')
async def stop(ctx):
    global track_queue
    track_queue = []
    voice_client = ctx.message.guild.voice_client
    if voice_client:
        voice_client.disconnect()  # disconnect
    await ctx.send("**Stopped playback and cleared queue**")


@bot.command(name='list', help='Returns a list of all tracks in library as a txt file')
async def list_tracks(ctx):
    async with ctx.typing():
        track_list = os.listdir(track_lib_dir)
        message_header = "Here's a list of all tracks on the system:"

        # Create txt file with track list
        with open(track_list_file, "w+") as file:
            for track in track_list:
                file.writelines(track + "\n")

        # Read track list file and send as message
        with open(track_list_file, "rb") as file:
            await ctx.send(message_header, file=discord.File(file, track_list_file))

        # Clean up
        os.remove(track_list_file)


@bot.command(name='queue', help='Returns the current queue')
async def queue(ctx):
    async with ctx.typing():
        global track_queue
        if not track_queue:
            await ctx.send("Queue is currently empty")
            return

        message_header = "**Top of queue:**"
        message = "{} \n```\n".format(message_header)
        track_queue_len = len(track_queue)

        # Cap the queue message list to 10 or less
        track_queue_max = 10 if track_queue_len >= 10 else track_queue_len
        for i in range(track_queue_max):
            message += (track_queue[i] + '\n')
        message += "\n```\n"

        # If track queue is much longer than track queue max, send remaining queue length
        if track_queue_len != track_queue_max:
            message += "**+{} more tracks in queue**".format(track_queue_len - track_queue_max)

        await ctx.send(message)


@bot.command(name='shuffle', help="Fills the queue with a specified number of random tracks from the library")
async def shuffle(ctx, num_shuffle=10):
    async with ctx.typing():
        global track_queue
        track_list = os.listdir(track_lib_dir)
        random.shuffle(track_list)

        # Adds 10 random tracks to shuffle
        track_queue += track_list[0:num_shuffle]
        await ctx.send("Queue now filled with a shuffled playlist")


@bot.command(name='add', help='Adds a track to library')
async def add(ctx):  # triggers when a message is sent
    async with ctx.typing():
        if ctx.message.attachments:  # if message has an attached file or image
            for attachment in ctx.message.attachments:
                if attachment.content_type in file_formats:  # check attachment type
                    if attachment.filename not in os.listdir(track_lib_dir):  # check if file already exists
                        r = requests.get(attachment.url, allow_redirects=True)  # if not, download file from url
                        # write contents of download request to folder
                        open(os.path.join(track_lib_dir, attachment.filename), 'wb').write(r.content)
                        await ctx.send("Added track: {}".format(attachment.filename))
                    else:
                        await ctx.send("Track is already in library: {}".format(attachment.filename))
                else:
                    await ctx.send("Unsupported file format {}".format(attachment.content_type))


@bot.command(name='search', help='Searches the library for a track')
async def search(ctx, *args):
    search_string = ""
    for arg in args:
        search_string += (str(arg) + " ")
    if search_string:
        await ctx.send("**Closest match:** {}".format(keyword_search(search_string)))
    else:
        await ctx.send("**No string provided:**")


@tasks.loop(seconds=5)
async def play_track(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client
    while len(track_queue) > 0:
        track_name = track_queue[0]
        track_path = os.path.join(track_lib_dir, track_name)
        if not os.path.exists(track_path):
            await ctx.send("**Does not exist:** {}".format(track_name))
            track_queue.pop(0)
            return
        if voice_channel:
            voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=track_path))
        await ctx.send("**Now Playing:** {}".format(track_name))
        # Wait if voice channel is playing or is paused
        while voice_channel.is_playing() or voice_channel.is_paused():
            await asyncio.sleep(3)
        # Handle a queue clear while playing a track
        if track_queue:
            track_queue.pop(0)


def keyword_search(keywords):
    # search and find closest match to keywords in the track library. Return only 1 closest match. Cutoff represents
    # the match threshold.
    track_list = os.listdir(track_lib_dir)
    for i in range(len(track_list)):
        track_list[i] = track_list[i]
    match, ratio = process.extractOne(keywords, track_list)    #match using new library
    if not match:  # if there are no matches, return something to indicate this
        return
    else:  # if there is a match, search the library for that match and send the appropriate path to play
        if ratio > 0.6:
            return match
        else:
            return


def search_library(track_name):
    track_path = os.path.join(track_lib_dir, track_name)
    return os.path.exists(track_path)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
