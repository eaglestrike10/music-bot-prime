import re
from discord.ext import commands, tasks
from fuzzywuzzy import process
import requests
import discord
import asyncio
import random
import os

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!', intents=intents)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
file_formats = ["audio/mpeg", "video/webm"]
track_lib_dir = "music"
pl_lib_dir = "playlist"    #directory to playlists
selected_pl = ""           #currently selected playlist
track_list_file = "track_list.txt"
track_queue = []


######################################### [ TRACK MANIPULATION FUNCTIONS ] #########################################

@bot.command(name='play', help='Plays a track specified by user')
async def play(ctx, *args):
    voice_client = ctx.message.guild.voice_client
    if not voice_client:  # check if user issuing command is connected to a channel
        if not ctx.message.author.voice:  # if not, write error
            await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
            return
        else:  # attempt connection to voice channel
            channel = ctx.message.author.voice.channel
        await channel.connect()

    if args:
        track_name = ""
        for arg in args:
            track_name += (str(arg) + " ")
        track_name = keyword_search(track_name)
        await ctx.send("**Closest match:** {}".format(track_name))
        if track_name:
            track_queue.append(track_name)
            await ctx.send('**Added to queue:** {}'.format(track_name))
        else:
            await ctx.send("**Does not exist:** {}".format(track_name))

    if not play_track.is_running():
        play_track.start(ctx)


@bot.command(name='playtop', help='Adds a track specified by the user to the top of the queue')
async def playtop(ctx, *args):
    voice_client = ctx.message.guild.voice_client
    if not voice_client:  # check if user issuing command is connected to a channel
        if not ctx.message.author.voice:  # if not, write error
            await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
            return
        else:  # attempt connection to voice channel
            channel = ctx.message.author.voice.channel
        await channel.connect()

    if args:
        track_name = ""
        for arg in args:
            track_name += (str(arg) + " ")
        track_name = keyword_search(track_name)
        await ctx.send("**Closest match:** {}".format(track_name))
        if track_name:
            track_queue.insert(1, track_name)
            await ctx.send('**Added to top of queue:** {}'.format(track_name))
        else:
            await ctx.send("**Does not exist:** {}".format(track_name))

    if not play_track.is_running():
        play_track.start(ctx)


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
        await voice_client.disconnect()  # disconnect
    await ctx.send("**Stopped playback and cleared queue**")
    play_track.stop()


######################################### [ QUEUE FUNCTIONS ] #########################################

@bot.command(name='queue', help='Returns the current queue')
async def queue(ctx):
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
    global track_queue
    track_list = os.listdir(track_lib_dir)
    random.shuffle(track_list)

    # Adds 10 random tracks to shuffle
    track_queue += track_list[0:num_shuffle]
    await ctx.send("Queue now filled with a shuffled playlist")


######################################### [ LIBRARY FUNCTIONS ] #########################################

@bot.command(name='add', help='Adds a track to library')
async def add(ctx):  # triggers when a message is sent
    if ctx.message.attachments:  # if message has an attached file or image
        for attachment in ctx.message.attachments:
            if attachment.content_type in file_formats:  # check attachment type
                filename = normalize_filename(attachment.filename)
                if filename not in os.listdir(track_lib_dir):  # check if file already exists
                    r = requests.get(attachment.url, allow_redirects=True)  # if not, download file from url
                    # write contents of download request to folder
                    open(os.path.join(track_lib_dir, filename), 'wb').write(r.content)
                    await ctx.send("Added track: {}".format(filename))
                else:
                    await ctx.send("Track is already in library: {}".format(filename))
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


@bot.command(name='list', help='Returns a list of all tracks in library as a txt file')
async def list_tracks(ctx):
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


######################################### [ PLAYLIST COMMANDS ] #########################################
#use track_lib_dir as currently selected playlist? or create new variable?
#track library will most likely need some restructuring

@bot.command(name='plc', help="Creates a playlist with the specified name")
async def plc(ctx, *args):
    ##concatinate all arguments for playlist name into single string
    name = ""
    for arg in args:
        name +=(str(arg)+" ")
    name += ".txt"
    #create hypothetical path to file
    playlistPath = os.path.join(pl_lib_dir, name)
    

    #check if playlist with specified name already exists
    if os.path.exists(playlistPath):
        await ctx.send("Specified playlist already exists!")
        return
    #create playlist if not duplicate
    else:
        #create empty txt file with playlist name
        f = open(playlistPath, 'rw')
        f.close
        await ctx.send("Playlist created!")
        return



@bot.command(name='pls', help="Selects playlist with specified name")
async def pls(ctx, *args):
    name = ""
    #concatenate args from command to create name to search for
    for arg in args:
        name +=(str(arg)+" ")

    #search for matching playlist
    match = pl_search(name)
    #if a match is found
    if match:
        #adjust selected playlist path 
        selected_pl = match
        #send success message 
        await ctx.send("***" + match + "*** is now the selected playlist")
        return
    else:
        #if no match, send failure message
        await ctx.send("There is no playlist with that name.")
        return


@bot.command(name='pld', help="Deletes a playlist with the specified name")
async def pld(ctx, *args):
    ##concatinate all arguments for playlist name into single string
    name = ""
    for arg in args:
        name +=(str(arg)+" ")
    name += ".txt"
    #create hypothetical path to file
    playlistPath = os.path.join(pl_lib_dir, name)

    #check if playlist with specified name already exists
    if os.path.exists(playlistPath):
        #if it does, delete it
        os.remove(playlistPath)
        await ctx.send("Playlist deleted!")
        return
    #create playlist if not duplicate
    else:
        #create empty txt file with playlist name
        await ctx.send("Specified playlist does not exists!")
        return


@bot.command(name='pla', help="Adds a track to the currently selected playlist")
async def pla(ctx, *args):
    playlist_path = os.path.join(pl_lib_dir, selected_pl)
    f = open(playlist_path, 'r')
    track_list = f.readlines()
    #concatinate user keywords into one string
    for arg in args:
        track_name +=(str(arg)+" ")
    
    #search selected playlist to see if the song already exists
    match = pl_keyword_search(track_name)
    
    if match:
        #check to see if track already exists in selected playlist
        for track in track_list:
            if track.strip("\n") == match:
                await ctx.send( "***" + match + "***" + " is already in the playlist " + selected_pl + ".")
                return

        #if track does not exist in playlist already, add it
        f = open(playlist_path, 'a')
        f.write(match + "\n")
        return
    else:
        #if no track match is found
        await ctx.send("Specified track does not exist")
        return

    
@bot.command(name='plr', help="Removes a track to the currently selected playlist")
async def plr(ctx, *args):
    exists = False
    #list path to the selected playlist
    playlist_path = os.path.join(pl_lib_dir, selected_pl)
    #read all tracks in to playlist into a track list
    f = open(playlist_path, 'r')
    track_list = f.readlines()

    #concatenate argument inputs for keyword search
    for arg in args:
        track_name +=(str(arg)+" ")

    #keyword search
    match = pl_keyword_search(track_name)

    #if there is a keyword match
    if match:
        for track in track_list:
            if track.strip("\n") == match:
                exists = True
        
        #if the entry exisits in the playlist, rewrite playlist while removing entry we want deleted
        if(exists):
            with open(playlist_path, 'w') as f:
                for track in track_list:
                    if track.strip("\n") != match:
                        f.write(track)
        return

    #if no match is found for keywords
    else:
        await ctx.send("Specified track does not exist")
        return


@bot.command(name='listpl', help="Lists all available playlists")
async def listpl(ctx):
    pl_list = os.listdir(pl_lib_dir)
    message_header = "Here's a list of all playlists on the system:"

    # Create txt file with pl list
    with open(pl_list_file, "w+") as file:
        for pl in pl_list:
            file.writelines(pl + "\n")

    # Read pl list file and send as message
    with open(pl_list_file, "rb") as file:
        await ctx.send(message_header, file=discord.File(file, pl_list_file))

    # Clean up
    os.remove(pl_list_file)


######################################### [ NON COMMAND FUNCTIONS ] #########################################

def normalize_filename(filename_string: str):
    filename, extension = os.path.splitext(filename_string)

    regex = re.compile(r"(\W|_)+", re.ASCII | re.MULTILINE)

    # Applies the regex expression substituting all matches by spaces
    normal_filename = regex.sub(' ', filename)

    return f'{normal_filename}{extension}'


def normalize_library():
    # Iterate renaming process for every single track in the track library
    for filename in os.listdir(track_lib_dir):
        # get old filename path
        old_name = os.path.join(track_lib_dir, filename)
        # generate corrected filename with path
        new_name = os.path.join(track_lib_dir, normalize_filename(filename))
        # replace old filename with new filename
        os.rename(old_name, new_name)


@tasks.loop(seconds=5)
async def play_track(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client
    voice_client = ctx.message.guild.voice_client

    if not voice_channel:
        return
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

    # Exit voice channel when queue is emptied
    if voice_client:
        await voice_client.disconnect()  # disconnect


def pl_search(keywords):
    # search and find closest match to keywords in the list of playlists. Return only 1 closest match
    pl_list = os.listdir(pl_lib_dir)
    match, ratio = process.extractOne(keywords, pl_list)    # match using fuzzywuzzy library
    if not match:  # if there are no matches, return something to indicate this
        return
    else:  # if there is a match, return matchj
        if ratio > 0.6:
            return match
        else:
            return


def pl_keyword_search(keywords):
    # search and find closest match to keywords in the currently selected playlist. Return only 1 closest match
    playlistPath = os.path.join(pl_lib_dir, selected_pl)
    f = open(playlistPath, 'r')
    track_list = f.readlines()
    match, ratio = process.extractOne(keywords, track_list)    # match using fuzzywuzzy library
    if not match:  # if there are no matches, return something to indicate this
        return
    else:  # if there is a match, search the library for that match and send the appropriate path to play
        if ratio > 0.6:
            return match
        else:
            return


def keyword_search(keywords):
    # search and find closest match to keywords in the track library. Return only 1 closest match. Cutoff represents
    # the match threshold.
    track_list = os.listdir(track_lib_dir)
    for i in range(len(track_list)):
        track_list[i] = track_list[i]
    match, ratio = process.extractOne(keywords, track_list)    # match using fuzzywuzzy library
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
    normalize_library()
    bot.run(DISCORD_TOKEN)
