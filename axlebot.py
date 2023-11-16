import asyncio
import discord
import os
from yt_dlp import YoutubeDL
from pytube import YouTube, Playlist, Search
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import gc
import requests
import time
from PIL import Image
import requests
import io
from song import Song
import random


client_id = "SPOTIFY_CLIENT_ID" 
client_secret = "SPOTIFY_CLIENT_SECRET"  

# Create an instance of the Spotipy client
client_credentials_manager = SpotifyClientCredentials(
    client_id=client_id, client_secret=client_secret
)

sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)
intents.voice_states = True
voice_clients = {}
song_queue = []
name_id = {}
adding_spotify_songs = False
adding_youtube_songs = False
list_of_tuples_for_synced_lyrics = []
start_time = 0
showing_lyrics = False
acceptable_input_delay = 4
time_elapsed_since_last_command = 0
time_last_message_was_sent = time.time()
list_of_vid_dets = []
list_of_yt_embed_messages = []
current_song_duration = 0
paused_time = 0
progress_bar_task = None
synced_lyrics_task = None
commands_list_aliases = {
    "play": ["-p", "-play"],
    "queue": ["-q", "-queue"],
    "lyrics": ["-l", "-lyrics"],
    "skip": ["-skip"],
    "resume": ["-res", "-resume"],
    "search": ["-search", "-s"],
    "pause": ["-pause"],
    "delete": ["-del", "-delete"],
    "stop": ["-stop"],
    "help": ["-help"],
    "repeat": ["-rep", "-repeat"],
    "playnext": ["-pn", "-playnext", "-playn", "-pnext"],
    "shuffle": ["-shuffle"],
    "yt_skip": ["-skip yt"],
    "spot_skip": ["-skip spot"]
}

command_list = [
    "-l", "-lyrics",
    "-skip", "-skip spot",
    "-skip yt", "-s",
    "-p", "-play",
    "-search", "-q",
    "-queue", "-pause",
    "-res", "-resume",
    "-del", "-stop",
    "-help","-rep",
    "-repeat","-pn",
    "-playnext","-playn",
    "-pnext", "-shuffle"
]

SPOTIFY_PLAYLIST, YOUTUBE_PLAYLIST = (1,2)

def is_valid_command(user_message):
    return user_message.lower() in command_list

def search_youtube_video(query):
    # Perform the search for videos
    search_results = Search(query)
    print(search_results)

    # Retrieve the URL of the first recommended video
    if len(search_results.results) > 0:
        video_url = (
            f"https://www.youtube.com/watch?v={search_results.results[0].video_id}"
        )
        return (
            video_url,
            search_results.results[0].title,
            search_results.results[0].length,
        )

    return None


@client.event
async def on_voice_state_update(member, before, after):
    global song_queue
    is_bot = member.bot
    if is_bot and after.channel == None:
        song_queue = []


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


async def play(voice_client,song, channel):
    global current_song_duration
    global start_time
    global list_of_tuples_for_synced_lyrics
    global progress_bar_task

    if song.is_spot:
        name_id[song.name] = 1
    elif song.is_yt:
        name_id[song.name] = 2
    else:
        name_id[song.name] = 0
    song_queue.append(song)
    current_song_duration = song.duration
    start_time = time.time()

    progress_bar_task = asyncio.create_task(embed_creator_sender_with_progress_bar(song, channel))
    list_of_tuples_for_synced_lyrics = get_closest_match_lyrics(song.name)
    start_time = time.time()
    voice_client.play(song.player,after=lambda e: asyncio.ensure_future(play_next(voice_client, channel), loop=voice_client.loop))


@client.event
async def on_message(message):
    global list_of_vid_dets
    global list_of_tuples_for_synced_lyrics
    global showing_lyrics
    global adding_spotify_songs
    global adding_youtube_songs
    global song_queue
    global start_time
    global acceptable_input_delay
    global time_elapsed_since_last_command
    global time_last_message_was_sent
    global list_of_yt_embed_messages
    global synced_lyrics_task
    global progress_bar_task
    message_content = message.content
    author = message.author
    try:
        prefix = message_content.split()[0]
    except:
        print("ignore")
        return
    if not author.bot:
        if message.reference is not None:
            for i in range(len(list_of_yt_embed_messages)):
                if message.reference.message_id == list_of_yt_embed_messages[i]:
                    await message.channel.send("Hold on, this may take a bit...")
                    await download_and_send_yt_vid(
                        message, list_of_vid_dets[i], int(message_content) - 1
                    )
        if not is_valid_command(prefix):
            return
        time_this_message_was_sent = time.time()
        time_elapsed_since_last_command = time_this_message_was_sent - time_last_message_was_sent
        print(time_elapsed_since_last_command)
        time_last_message_was_sent = time_this_message_was_sent
        if time_elapsed_since_last_command > acceptable_input_delay:
            if message_content.lower() in commands_list_aliases["help"]:
                await message.channel.send(
                    "```AxleBot uses many different commands which start with '-' they are:\n-help (obviously)\n-play or -p [song name or spotify/YouTube music playlist link or url]\n-pause \n-resume or -res\n-stop\n-q or -queue\n-skip \n-skip spot (to skip every Spotify playlist song))\n-skip yt (to skip every YouTube playlist song)\n-del [position of song]\n-rep [optional: number of times the song should be repeated] (-rep on its own will repeat a song once)\n-l or -lyrics (will show live lyrics - the best it can\n-s [Query/search term for YouTube] e.g '-s cat videos'```"
                )
            if message_content.lower() in commands_list_aliases["lyrics"]:
                if showing_lyrics:
                    await message.channel.send(
                        "The lyrics are either already being displayed or did not exist"
                    )
                    return
                if len(song_queue) == 0:
                    await message.channel.send("There is no song currently playing.")
                    return
                showing_lyrics = True
                if list_of_tuples_for_synced_lyrics is None:
                    await message.channel.send(
                        embed=discord.Embed(
                            title="Lyrics not found",
                            description="No lyrics were found for this song. "
                            "It may not exist on Spotify or there "
                            "was an error.",
                            colour=0xFF0000,
                        )
                    )
                    return
                synced_lyrics_task = await send_lyrics_embed(list_of_tuples_for_synced_lyrics, message)
            if prefix.lower() in commands_list_aliases["repeat"]:
                song_to_repeat = song_queue[0]
                song_to_repeat.player = song_to_repeat.get_fresh_player()
                try:
                    args = message_content.split()
                    if len(args) == 2:
                        num = int(args[1])
                        if num < 1 and num < 15:
                            await message.channel.send(f"Please enter a valid number of times you want the song to be repeated (1-15)")
                            return
                        else:
                            await message.channel.send(f"{song_queue[0].name} will be repeated `{num}` times")

                            for _ in range(num):
                                song_queue.insert(1, song_to_repeat)
                            return
                                                    
                except Exception as e:
                    await message.channel.send(f"Python Error: {e}")
                    return
                await message.channel.send(f"The currently playing song: `{song_queue[0].name}` will be repeated next")
                song_queue.insert(1, song_to_repeat)
            if message_content.lower() in commands_list_aliases["spot_skip"]:
                await skip_playlist(message, type = SPOTIFY_PLAYLIST)
            if message_content.lower() in commands_list_aliases["yt_skip"]:
                await skip_playlist(message, type = YOUTUBE_PLAYLIST)
            if prefix.lower() in commands_list_aliases["delete"]:
                try:
                    pos = int(message_content.split(prefix + " ")[1])
                except Exception as e:
                    await message.channel.send(f"Python Error:{e}\nYou must provide a positional index for what song you want to delete. For example `del 1` to delete the first song in the queue")
                    return
                if pos < 1 or pos > len(song_queue):
                    await message.channel.send("The position you entered doesn't make sense, perhaps try again")
                else:
                    index = pos - 1
                    await message.channel.send(
                        f"**{song_queue[index].name}** has been deleted"
                    )
                    #del name_id[song_queue[index].name]
                    del song_queue[index]
            if prefix.lower() in commands_list_aliases["playnext"]:
                query = message_content.split(prefix + " ")[1]
                song = await Song.CreateSong(query)
                try:
                    song_queue.insert(1, song)
                except Exception as e:
                    add_to_queue(song)
                await message.channel.send(f"**{song.name}** will play next in the queue after the current playing song")
            if prefix.lower() in commands_list_aliases["play"]:
                await play_song_request(message, author, message_content, prefix)
            elif message_content.lower() in commands_list_aliases["pause"]:
                if author.voice is not None:
                    try:
                        voice_clients[message.guild.id].pause()
                        paused_time = time.time()
                        progress_bar_task.set()

                        await message.channel.send(
                            "The song has been paused, use -res to resume it"
                        )
                    except Exception as err:
                        print(err)
                else:
                    await message.channel.send(
                        f"{message.author.display_name}, you need to be in a voice channel to pause songs"
                    )

            elif message_content.lower() in commands_list_aliases["resume"]:
                if author.voice is not None:
                    try:
                        if voice_clients[message.guild.id].is_paused():
                            voice_clients[message.guild.id].resume()
                            paused_time = time.time() - paused_time
                            await message.channel.send(
                                "Resumed, your song is now playing..."
                            )
                        else:
                            await message.channel.send(
                                "Your song is not paused, so you cant resume it\n```If your song IS paused right now then there is something wrong with the bot :(```"
                            )
                    except Exception as err:
                        print(err)
                else:
                    await message.channel.send(
                        f"{message.author.display_name}, you need to be in a voice channel to resume songs"
                    )

            elif message_content.lower() in commands_list_aliases["stop"]:
                if author.voice is not None:
                    try:
                        song_queue = []
                        list_of_tuples_for_synced_lyrics = []
                        voice_clients[message.guild.id].stop()
                        adding_spotify_songs = False
                        adding_youtube_songs = False
                        showing_lyrics = False
                        await message.channel.send(
                            "```Music stopped, use `-p` to start playing music again```"
                        )
                        gc.collect()
                    except Exception as err:
                        print(err)
                else:
                    await message.channel.send(f"You must be in a voice channel to use `{message.content}`")
            if message_content.lower() in commands_list_aliases["skip"]:
                if author.voice is not None:
                    try:
                        vc = voice_clients[message.guild.id]
                        vc.stop()
                        print("stopped")
                        if len(song_queue) == 0:
                            await message.channel.send(
                                "There are no songs currently playing."
                            )
                        if len(song_queue) > 1:
                            await message.channel.send(
                                "The song has been skipped. The next song in the queue will start playing now."
                            )
                    except Exception as err:
                        print(err)
                else:
                    await message.channel.send("You must be in a voice channel to use `-skip`")

            if message_content.lower() in commands_list_aliases["queue"]:
                await print_queue(message.channel)
            if message_content.lower() in commands_list_aliases["shuffle"]:
                shuffle_track = song_queue[1:]
                random.shuffle(shuffle_track)
                song_queue = [song_queue[0]] + shuffle_track
                await message.channel.send("The queue has been shuffled, use `-q` to see the new queue layout")
            if prefix.lower() in commands_list_aliases["search"]:
                query = message_content.split(prefix + " ")[1]
                search_results = Search(query).results[:10]
                vid_dets = []
                for yt_vid in search_results:
                    video_url = f"https://www.youtube.com/watch?v={yt_vid.video_id}"
                    video_title = yt_vid.title
                    video_author = yt_vid.author
                    video_views = yt_vid.views
                    video_length = yt_vid.length
                    vid_dets.append(
                        (
                            video_title,
                            video_url,
                            video_author,
                            video_views,
                            video_length,
                        )
                    )
                latest_yt_embed_message = await create_and_send_yt_search_embed(query, message, vid_dets)
                list_of_vid_dets.append(vid_dets)
                list_of_yt_embed_messages.append(latest_yt_embed_message.id)
        else:
            await message.channel.send(f"Slow down! You gotta wait `{acceptable_input_delay}` seconds between sending messages")

def add_to_queue(song, type=None, pos=None):
    if pos == None:
        song_queue.append(song)
    else:
        song_queue.insert(pos, song)

    if type == SPOTIFY_PLAYLIST:
        name_id[song.name] = 1
    elif type == YOUTUBE_PLAYLIST:
        name_id[song.name] = 2
    else:
        name_id[song.name] = 0

async def create_and_send_yt_search_embed(query, message, vid_dets):
    embed = discord.Embed(title=f"Search results for '{query}'", colour=0xF50000)
    embed.set_author(name=f"Search requested by {message.author.display_name}")
    i = 1
    for vid in vid_dets:
        embed.add_field(
            name=f"[{i}] {vid[0]}",
            value=f"Source: {vid[2]}\nView Count: {vid[3]}\nDuration = {convert_duration(vid[4])}",
            inline=False,
        )
        i += 1
    yt_search_embed = await message.channel.send(embed=embed)
    await message.channel.send(
        "Reply to the ^^ABOVE^^ message with a number to download that video (if its small enough)\n```E.g. If you replied '1' to that message it would download the first result```"
    )
    return yt_search_embed

async def play_song_request(message, author, message_content, prefix, pos=None):
    query = message_content.split(prefix + " ")[1]
    if message.author.voice is not None:
        is_spotify_playlist = False
        is_youtube_playlist = False
        std_yt_song = None
        spotify_playlist_info, youtube_playlist_info = [], []
        if "open.spotify.com/playlist/" in query:
            spotify_playlist_info = Song.get_spotify_info(query)
            is_spotify_playlist = True
            adding_spotify_songs = True
            await message.channel.send("The Spotify playlist has been added to the queue in the order shown. Do `-skip spot` to skip every Spotify song in the queue. Otherwise do `-q` to see the queue. ```Note: It may take some time to load in every track```")
        elif "youtube.com" in query and "list=" in query:
            youtube_playlist_info = Song.get_youtube_playlist_info(query)
            is_youtube_playlist = True
            adding_youtube_songs = True
            await message.channel.send(
                "The YouTube playlist has been added. Do `-skip yt` to skip every YouTube song in the queue. Otherwise do `-q` to see the queue. ```Note: It may take some time to load in every track```"
            )
        elif "youtube.com" in query and "list=" not in query:
            std_yt_song = await Song.SongFromYouTubeURL(query)
        else:
            std_yt_song = await Song.CreateSong(query)
        if len(song_queue) >= 1:
            if is_spotify_playlist:
                for track in spotify_playlist_info:
                    if not adding_spotify_songs:
                        break
                    song = await Song.SpotifySong(track[0], track[1], track[2])
                    add_to_queue(song, SPOTIFY_PLAYLIST, pos = pos)
                    await asyncio.sleep(2.5)

            elif is_youtube_playlist:
                for url in youtube_playlist_info:
                    if not adding_youtube_songs:
                        break
                    song = await Song.YouTubePlaylistSong(url)
                    add_to_queue(song, YOUTUBE_PLAYLIST, pos = pos)
                    await asyncio.sleep(2.5)
            else:
                add_to_queue(std_yt_song)
                await message.channel.send(f"**{std_yt_song.name}** has been added to the queue in position `{len(song_queue)}`")
        else:
            vc = voice_clients.get(message.guild.id, None)
            if vc == None:
                vc = await author.voice.channel.connect()
                voice_clients[message.guild.id] = vc
            elif not vc.is_connected:
                vc = await author.voice.channel.connect()
                voice_clients[message.guild.id] = vc

            if is_spotify_playlist:
                firstSong = await Song.SpotifySong(spotify_playlist_info[0][0], spotify_playlist_info[0][1], spotify_playlist_info[0][2])
                await play(vc, firstSong, message.channel)
                for track in spotify_playlist_info[1:]:
                    if not adding_spotify_songs:
                        break
                    song = await Song.SpotifySong(track[0], track[1], track[2])
                    add_to_queue(song, SPOTIFY_PLAYLIST, pos = pos)
                    await asyncio.sleep(2.5)

            elif is_youtube_playlist:
                firstSong = await Song.YouTubePlaylistSong(youtube_playlist_info[0])
                await play(vc, firstSong, message.channel)
                for url in youtube_playlist_info[1:]:
                    if not adding_youtube_songs:
                        break
                    song = await Song.YouTubePlaylistSong(url)
                    add_to_queue(song, type = YOUTUBE_PLAYLIST, pos = pos)
                    await asyncio.sleep(2.5)
            else:
                await play(vc, std_yt_song, message.channel)
    else:
        await message.channel.send(f"{message.author.display_name}, you need to be in a voice channel to play music")


async def play_next(vc, channel):
    global start_time
    global list_of_tuples_for_synced_lyrics
    global showing_lyrics
    global current_song_duration
    if len(song_queue) >= 1:
        # Remove the current song from the queue
        list_of_tuples_for_synced_lyrics = []
        showing_lyrics = False
        song_queue.pop(0)
        if len(song_queue) > 0:
            list_of_tuples_for_synced_lyrics = get_closest_match_lyrics(song_queue[0].name)
            current_song_duration = song_queue[0].duration
            start_time = time.time()
            asyncio.create_task(embed_creator_sender_with_progress_bar(song_queue[0],channel))
            start_time = time.time()
            vc.play(song_queue[0].player, after=lambda e: asyncio.ensure_future(play_next(vc, channel), loop=vc.loop))
        else:
            await channel.send(embed = discord.Embed(title="The song queue is empty!",description="The queue is empty use `-p [song_name]` to play and add songs to the queue",colour=0x00b0f4))
    else:
        await channel.send(embed = discord.Embed(title="The song queue is empty!",description="The queue is empty use `-p [song_name]` to play and add songs to the queue",colour=0x00b0f4))


def get_closest_match_lyrics(song):
    print(f"song is: {song}")
    most_relevant_track = sp.search(q=song, limit=1, type="track")["tracks"]["items"][0]
    return get_lyrics(most_relevant_track["id"])


def get_lyrics(spot_track_id):
    api_url = (
        f"https://spotify-lyric-api-984e7b4face0.herokuapp.com/?trackid={spot_track_id}"
    )

    response = requests.get(api_url)

    data = response.json()

    if data["error"]:
        return None

    for i in range(len(data["lines"])):
        list_of_tuples_for_synced_lyrics.append(
            (int(data["lines"][i]["startTimeMs"]), data["lines"][i]["words"])
        )

    print(list_of_tuples_for_synced_lyrics)
    return list_of_tuples_for_synced_lyrics


def get_current_playing_line(list_of_tuples_for_synced_lyrics, start_index):
    global start_time
    global paused_time
    elapsed_time = ((time.time() - start_time) - paused_time) * 1000
    for i in range(len(list_of_tuples_for_synced_lyrics))[start_index:]:
        if list_of_tuples_for_synced_lyrics[i][0] > elapsed_time:
            return i


def extract_embed_color(thumbnail_url):

    response = requests.get(thumbnail_url)
    image_data = response.content

    image = Image.open(io.BytesIO(image_data))

    image = image.resize((100, 100))

    left = 25
    top = 25
    right = 75
    bottom = 75

    cropped_image = image.crop((left, top, right, bottom))
    average_color = cropped_image.resize((1, 1)).getpixel((0, 0))

    hex_color = (average_color[0] << 16) + (average_color[1] << 8) + average_color[2]

    return hex_color


def calculate_progress():
    global current_song_duration
    global paused_time
    global start_time
    current_time = time.time()
    elapsed_time = (current_time - start_time) - paused_time
    progress = (elapsed_time / current_song_duration) * 100
    return min(progress, 100)  # Ensure progress doesn't exceed 100%


async def embed_creator_sender_with_progress_bar(song, channel, progress_message = None):
    global current_song_duration

    if len(song_queue) > 0 and song.name != song_queue[0].name:
        return

    desc = f"{song.name}"
    colour=extract_embed_color(song.thumbnail_url)

    if song.is_spot:
        embed = discord.Embed(
            title="Now playing from Spotify...",
            description=desc,
            colour=colour,
        )
    elif song.is_yt:
        embed = discord.Embed(
            title="Now playing from a YouTube playlist...",
            description=desc,
            colour=colour,
        )
    else:
        embed = discord.Embed(
            title="Now playing...",
            description=desc,
            colour=colour,
        )

    embed.set_thumbnail(url=song.thumbnail_url)

    # Add the progress bar field to the embed
    progress = 0
    embed.add_field(name="Progress", value=update_progress_bar(progress), inline=False)

    embed.add_field(name="By", value=f"{song.artist}", inline=True)
    embed.add_field(
        name="Duration", value=convert_duration(current_song_duration), inline=True
    )

    if progress_message is None:
        progress_message = await channel.send(embed=embed)

    # Simulate video playback with progress updates

    while progress < 94: # 94% ensures that this async function ends before the next song starts playing

        progress = calculate_progress()
        embed.set_field_at(0, name="Progress", value=update_progress_bar(progress))
        await progress_message.edit(embed=embed)
        await asyncio.sleep(1.5)

    # Update the progress bar to 100% when the video playback is complete
    embed.set_field_at(0, name="Progress", value=update_progress_bar(100))

    await progress_message.edit(embed=embed)

    progress_message = None

    return


async def skip_playlist(message, type):
    global adding_spotify_songs
    global adding_youtube_songs
    if type == SPOTIFY_PLAYLIST:
        await message.channel.send("All Spotify songs are being cleared from the queue...")
        adding_spotify_songs = False
    else:
        await message.channel.send("All Youtube playlist songs are being cleared from the queue...")
        adding_youtube_songs = False
    await asyncio.sleep(2.5)

    if (song_queue[0].is_spot and type == SPOTIFY_PLAYLIST) or (song_queue[0].is_yt and type == YOUTUBE_PLAYLIST):
        song_queue.insert(0, None)
        voice_clients[message.guild.id].stop()

    for i in range(len(song_queue) - 1, -1, -1):
        name = song_queue[i].name
        if name_id[name] == type:
            print(f"deleted {name}")
            del name_id[name]
            del song_queue[i]


async def print_queue(channel):
    if len(song_queue) != 0:
        opt = ""
        for i in range(len(song_queue)):
            if i == 0:
                opt += f"[{i+1}] **{song_queue[i].name}** => Now playing...\n"
            else:
                opt += f"[{i+1}] **{song_queue[i].name}**\n"
        opt += "\n(If a playlist has been added the tracks will be added slowly, so they wont all show up at once)"
        try:
            await channel.send(embed = discord.Embed(
                title="Queue of Songs",
                description=opt,
                colour=0x00b0f4,
            ))
        except Exception as e:
            await channel.send(embed = discord.Embed(
                title="Too many songs in queue",
                description="The queue will be managed internally, it is too long to send via Discord",
                colour=0xFFA500,
            ))
    else:
        await channel.send(embed = discord.Embed(title="The song queue is empty!",description="The queue is empty use `-p [song_name]` to play and add songs to the queue",colour=0x00b0f4))


def edit_current_playing_line(start_index, lyrics_as_list_of_tupes):
    lyrics = ""
    for i,time_words in enumerate(lyrics_as_list_of_tupes):
        if i == start_index:
            lyrics += f'**{time_words[1]}**\n'
        else:
          lyrics += time_words[1] + "\n"

    return lyrics


async def send_lyrics_embed(presentable_lyrics, message):
    lyrics = ""
    for time_words in presentable_lyrics:
        lyrics += time_words[1] + "\n"

    if (len(lyrics) > 4080):
        await message.channel.send(
            embed=discord.Embed(
            title="The lyrics were too long to send!",
            colour=0xFF0000,
            )
        )
        return

    asyncio.create_task(send_synced_lyrics(lyrics, presentable_lyrics, message))

async def send_synced_lyrics(plain_lyrics, presentable_lyrics, message):
    global showing_lyrics
    global start_time
    showing_lyrics = True
    current_index = 0

    lyrics_message = await message.channel.send(
          embed=discord.Embed(
              title="Lyrics from Spotify",
              description=plain_lyrics,
              colour=0x00b0f4,
          )
      )
    
    while showing_lyrics:
      temp_index = get_current_playing_line(presentable_lyrics, current_index)
      if temp_index is None:
          break
      if (temp_index > current_index):
        edited_lyrics = edit_current_playing_line(current_index, presentable_lyrics)
        await lyrics_message.edit(embed = discord.Embed(
                title="Lyrics from Spotify",
                description=edited_lyrics,
                colour=0x00b0f4,
            ))
        current_index = temp_index
      await asyncio.sleep(0.1)
    return


async def download_and_send_yt_vid(message, vid_dets, search_index):
    url = vid_dets[search_index][1]

    # Create a temporary file name for the video
    temp_file_name = "temp_video.mp4"

    # Download the YouTube video using pytube
    try:
        video = YouTube(url)
        streams = (
            video.streams.filter(file_extension="mp4").order_by("resolution").desc()
        )
        res = None
        for stream in streams:
            if stream.includes_audio_track and stream.filesize <= 25 * 1024 * 1024:
                res = stream.resolution
                stream.download(filename=temp_file_name)
                break

        if not os.path.exists(temp_file_name):
            await message.channel.send(
                "I went down all the way to 144p, and still the file size was more than what Discord would allow :("
            )
            return

        # Get the text channel where you want to send the video
        channel = message.channel

        # Open the video file in binary mode and send it as a file attachment
        with open(temp_file_name, "rb") as file:
            await channel.send(
                f"Downloaded the video in {res}. It is being sent now, this may also take a bit..."
            )
            await channel.send(file=discord.File(file, filename="video.mp4"))

    except Exception as e:
        await channel.send(
            f"An error occurred while downloading the video: {str(e)}"
        )

    finally:
        # Delete the temporary video file
        if os.path.exists(temp_file_name):
            os.remove(temp_file_name)


def convert_duration(duration):
    hours = duration // 3600
    minutes = (duration % 3600) // 60
    seconds = duration % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"


def update_progress_bar(progress):
    bar_length = 18
    filled_length = int(bar_length * progress / 100)
    empty_length = bar_length - filled_length
    bar = "█" * filled_length + "░" * empty_length
    return f"{bar}"


client.run("YOUR_DISCORD_BOT_TOKEN")
