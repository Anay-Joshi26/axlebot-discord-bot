
"""
This file is the primary message crafter. It will craft discord Embeds to send out. To use it, find the function, and pass in any neccessary params
"""

import requests
from PIL import Image
import asyncio
import time
import io
import discord
from typing import Optional, Literal
from models.song import Song, LyricsStatus
from discord.ext import commands
from models.playlist import Playlist
from datetime import datetime

# Colours for the embeds
COLOURS = {
    "error": 0xFF0000,
    "success": 0x00b0f4,
    "warning": 0xff9e42,
}

def craft_now_playing(song: Song, is_looping = False):
    embed = discord.Embed(
    title=(
        f"Now playing{' from YouTube Playlist' if song.is_playlist else ''}..." 
        if song.type == 'yt' 
        else f"Now playing from Spotify{' from Spotify Playlist' if song.is_playlist else ''}..."
    ),
    description=song.name,
    colour=extract_embed_color(song.thumbnail_url),
    )
    
    embed.set_thumbnail(url=song.thumbnail_url)

    current_song_duration = song.duration

    # Add the progress bar field to the embed

    progress = 0
    embed.add_field(name="Progress", value=update_progress_bar(progress), inline=True)

    embed.add_field(name="By", value=f"{song.artist}", inline=True)
    embed.add_field(
        name="Duration", value=convert_duration(current_song_duration), inline=True
    )
    #asyncio.create_task(update_progress_bar_embed(song, embed))
    return embed

def craft_playlist_added(type_of_playlist):
    embed = discord.Embed(title = f"{'Spotify' if type_of_playlist == 'spot' else 'YouTube'} Playlist Queued",
                    description=f"You have just queued a playlist in the default order.\n\nIt may take some time to queue every song in the playlist. There are some playlist specific commands you can use while a playlist is being played.\n\n**The first song should start to be queued shortly...**\n\nYou can inspect the queue to see the added songs via `-queue` or `q`.\n\n`-skip {'spot' if type_of_playlist == 'spot' else 'yt'}` skips the **current playing** {'Spotify' if type_of_playlist == 'spot' else 'YouTube'} playlist\n`-shuffle {'spot' if type_of_playlist == 'spot' else 'yt'}` will shuffle the **current playing** {'Spotify' if type_of_playlist == 'spot' else 'YouTube'} playlist",
                    colour=0x1ED760 if type_of_playlist == "spot" else 0xFF0033)

    return embed

def craft_song_added(song: Song):
    pass

def craft_bot_music_stopped(delete_after: int = 10):
    embed = discord.Embed(title="Music Playback Stopped",
                      description=f"Music playback has been stopped, the queue has been cleared and the bot has left the voice channel.",
                      colour=COLOURS["success"])

    embed.add_field(name="Delete After",
                    value=f"This message will be deleted in {delete_after} seconds",
                    inline=False)
    
    return embed

async def update_progress_bar_embed(song: Song, progress_embed: discord.Embed, song_message: discord.Message, update_interval: int | None = None):

    """
    This function will update the progress bar in the embed, and update/edit the message with the new progress bar at set intervals.
    The interval time can be set with the update_interval parameter.

    If it is set to None, the function will determine a more ideal interval time based on the duration of the song and the bar length to keep the event loop from being blocked by too many tasks.
    """


    progress = calculate_progress(song)
    bar_length = 18

    if update_interval is None:
        update_interval = max(1, (song.duration/bar_length) * 0.5)


    while progress < 95:
        progress = calculate_progress(song)
        progress_embed.set_field_at(0, name="Progress", value=update_progress_bar(progress, bar_length = bar_length))
        await song_message.edit(embed=progress_embed)
        await asyncio.sleep(update_interval)

        if progress > (bar_length-2)/bar_length:
            update_interval = 1.1

    progress_embed.set_field_at(0, name="Progress", value=update_progress_bar(100, bar_length = bar_length))
    await song_message.edit(embed=progress_embed)

def craft_delete_song(song: Song) -> discord.Embed:
    embed = discord.Embed(title=song.name,
                      description="The song has been **deleted** from the queue, and will not be played.\n\nYou can view the updated queue via `-queue` or `q`.",
                      colour=0x00b0f4)

    embed.set_author(name=song.artist)

    embed.set_thumbnail(url=song.thumbnail_url)

    return embed

def craft_move_song(song: Song, move_to: int) -> discord.Embed:
    embed = discord.Embed(title=song.name,
                      description=f"The song has been **moved** to position `{move_to}` in the queue.\n\nYou can view the updated queue via `-queue` or `-q`.",
                      colour=0x00b0f4)
    return embed


def update_progress_bar(progress, bar_length=18):
    filled_length = int(bar_length * progress / 100)
    empty_length = bar_length - filled_length
    bar = "█" * filled_length + "░" * empty_length
    return f"{bar}"

def calculate_progress(song):
    progress = (song.seconds_played / song.duration) * 100
    return min(progress, 100)  # Ensure progress doesn't exceed 100%

def convert_duration(duration):
    hours = duration // 3600
    minutes = (duration % 3600) // 60
    seconds = duration % 60

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes:02d}:{seconds:02d}"

def craft_lyrics_embed(lyrics: str, song_name: str, artist: str, status = LyricsStatus.FETCHED):
    if status == LyricsStatus.FETCHING:
        embed = discord.Embed(
            title="Lyrics are being fetched, please wait...",
            description="Getting lyrics can take a bit, please run this command again in a few seconds",
            colour=0xff9e42,
        )
        return embed
    elif status == LyricsStatus.ERROR:
        embed = discord.Embed(
            title="An error occurred while fetching the lyrics",
            description="",
            colour=0xff0000,
        )
        return embed
    elif status == LyricsStatus.NOT_STARTED:
        embed = discord.Embed(
            title="The fetching of lyrics has not started yet",
            description="",
            colour=0xff0000,
        )
        return embed
    elif status == LyricsStatus.NO_LYRICS_FOUND:
        embed = discord.Embed(
            title="Lyrics not found for this song",
            description="No close matching lyrics were found for this song with the name and artist",
            colour=0xff0000,
        )
        return embed
    try:
        embed = discord.Embed(
            title=f"Lyrics for {song_name} by {artist}",
            description=lyrics,
            colour = 0x00b0f4
        )
    except Exception as e:
        return discord.Embed(
            title=f"[TOO LONG TO SEND] Lyrics for {song_name} by {artist}",
            description="The lyrics for this song are too long to send via Discord",
            colour=0xff9e42,
        )

    return embed

def craft_queue_empty():
    embed = discord.Embed(
        title="The song queue is empty!",
        description=f"The queue is empty use `-p [song_name]` to play and add songs to the queue\n\n*Axlebot will leave the voice channel after 2 minutes of inactivity*",
        colour=0x00b0f4)
    return embed

def craft_queue(queue):
    if len(queue) == 0:
        return craft_queue_empty()
    
    print("Crafting queue")

    opt = ""
    for i in range(len(queue)):
        if i == 0:
            opt += f"[{i+1}] **{queue[i].name}** => Now playing...{' [LOOPED]' if queue.loop_current else ''}\n"
        else:
            opt += f"[{i+1}] **{queue[i].name}**\n"
    opt += "\n(If a playlist has been added the tracks will be added slowly, so they wont all show up at once)"


    try:
        return discord.Embed(
            title="Queue of Songs",
            description=opt,
            colour=0x00b0f4,
        )
    except Exception as e:
        return discord.Embed(
            title="Too many songs in queue",
            description="The queue will be managed internally, it is too long to send via Discord",
            colour=0xFFA500,
        )

def extract_embed_color(thumbnail_url):

    response = requests.get(thumbnail_url)
    image_data = response.content

    image = Image.open(io.BytesIO(image_data))

    image = image.resize((100, 100))

    left, top = 25, 25
    right, bottom = 75, 75

    cropped_image = image.crop((left, top, right, bottom))
    average_color = cropped_image.resize((1, 1)).getpixel((0, 0))

    hex_color = (average_color[0] << 16) + (average_color[1] << 8) + average_color[2]

    return hex_color

def craft_playlist_created(name: str) -> discord.Embed:

    embed = discord.Embed(title=f"{name}",
                      description=f"A playlist named \"{name}\" has been created and currently has `0` songs inside it. \n\nTo add your own songs you use the command:\n\n`-add_songs <Optional: Playlist name> <url 1> <url 2> <url 3> ...`\n\n OR\n\n Use the button below to add songs to this newly created playlist\n\nIf you choose to not provide a playlist name the songs will be added to the **last created playlist** which was created.\n\nYou can add up to 20 songs in one playlist, if you enter more than 20 links only the first 20 will be added.\n\nThe urls can be YouTube links or Spotify links (to individual songs), they **cannot** be Spotify or YouTube Playlist links.",
                      colour=0x00b0f4)

    #embed.set_author(name=f"Created By {author.display_name}")

    return embed

def craft_no_playlist_found(name: str):
    embed = discord.Embed(title="Playlist not found",
        description=f"No playlist named `{name}` was found, ensure you have created a playlist with that name or have spelt the name correctly",
        colour=0xff0000)
    return embed

def craft_songs_added_to_playlist(name: str, songs_added: list) -> discord.Embed:
    """
    Creates an embed message to show the songs that were added to the playlist.

    :param name: The name of the playlist

    :param songs_added: A list of song names that were added

    :return: A discord.Embed object
    """
    
    songs_description = "\n".join([f"{i+1}. **{song.name}**" for i,song in enumerate(songs_added)])
    
    embed = discord.Embed(
        title=f"Songs successfully added to {name}",
        description=f"The following songs were successfully added:\n\n{songs_description}",
        colour=COLOURS["success"]
    )
    
    return embed

def craft_custom_playlist_queued(name: str, playlist: Playlist) -> discord.Embed:
    embed = discord.Embed(
        title=f'"{name}" Playlist Queued',
        description="A custom playlist has been queued. \n\nEvery song inside the playlist has been added to the queue in the order shown below:\n\n",
        colour=COLOURS["success"]
    )

    for i, song in enumerate(playlist.songs):
        embed.description += f"{i+1}. {song.name}\n"

    embed.add_field(name="Total Songs", value=f"{len(playlist.songs)}", inline=True)
    embed.add_field(name="Total Duration", value=convert_duration(playlist.total_duration), inline=True)
    embed.add_field(name="Playlist Created At", value=datetime.fromtimestamp(playlist.created_at).strftime('%d/%m/%Y %H:%M'), inline=True)
    
    return embed

def craft_playlist_deleted(name: str) -> discord.Embed:
    """
    Creates an embed message to show that a playlist has been deleted.

    :param name: The name of the playlist

    :return: A discord.Embed object
    """
    
    embed = discord.Embed(
        title=f"Playlist deleted",
        description=f'The playlist named "{name}" has been successfully deleted',
        colour=COLOURS["success"]
    )
    
    return embed

def craft_songs_not_added(urls: list):
    """
    Creates an embed message to show the URLs that could not be converted into songs.

    :param urls: A list of URLs that could not be converted

    :return: A discord.Embed object
    """
    
    urls_description = "\n".join([f"**{url}**" for url in urls])
    
    embed = discord.Embed(
        title="Songs not added",
        description=f"The following \"urls\" could not be converted into songs:\n\n{urls_description}",
        colour=COLOURS["error"]
    )
    
    return embed

def craft_view_all_playlists(playlists: list) -> discord.Embed:
    """
    Creates an embed message to show all the playlists that the user has created.

    :param playlists: A list of playlist names

    :return: A discord.Embed object
    """

    n = len(playlists)

    description = "\n".join([f"{i+1}. {playlist.name}" for i,playlist in enumerate(playlists)])

    embed = discord.Embed(title="All Playlists",
                      description=f"The server currently has `{n}` playlists, they are:\n\n{description}\n\nRun `-playlists <Playlist Name>` to see the songs for a particular playlist",
                      colour=COLOURS["success"])

    return embed

def craft_songs_in_playlist(playlist_name: str, songs: list) -> discord.Embed:
    """
    Creates an embed message to show all the songs in a playlist.

    :param playlist_name: The name of the playlist

    :param songs: A list of song names

    :return: A discord.Embed object
    """

    n = len(songs)

    description = "\n".join([f"{i+1}. {song.name}" for i,song in enumerate(songs)])

    embed = discord.Embed(title=f"Songs in {playlist_name}",
                      description=f"The playlist named `{playlist_name}` currently has `{n}` songs, they are:\n\n{description}",
                      colour=0x00b0f4)

    return embed

def craft_default_help_command():
    embed = discord.Embed(title="Help commands",
                      description="AxleBot can do many things, scroll through and select the option which you would like to see the help commands for.\n\n**Message spamming**\nEvery command has cooldown to prevent spamming. This is `5` seconds per message for most people with `1` second for premium guilds/servers. The `-help` command has a `1` second cooldown **for all**.\n\n**Other things to note**\nThe bot keeps some persistent info about a server such as whether it is premium and the playlists created. Sometimes this info can take a few seconds to retrieve if you have been inactive for a while. **Premium users will benefit from this rarely being a problem.** These measures are necessary for the bot to be accessible by everyone and to not crash the bot itself.\n\nPremium users also have other benefits, soon to come!",
                      colour=0x00b0f4)

    embed.set_author(name="AxleBot Help Commands")

    return embed

def craft_playing_music_help_command():

    embed = discord.Embed(title="Playing Music",
                      description="AxleBot at its core a powerful music bot which supports music playback from YouTube and Spotify.\n\n__To play a song **with a query**__\n`-p <Query>`\nE.g.,  `-p rick roll`\n\n__To play a song **with a YouTube URL**__\n`-p <YouTube URL>` \nE.g., `-p https://www.youtube.com/watch?v=dQw4w9WgXcQ`\nTo work the URL must be in this format of `https://www.youtube.com/watch?v=<ID>`\n\n__To play a song **with a Spotify Track URL**__\n`-p <Spotify Track URL>` \nE.g., `-p https://open.spotify.com/track/7ixxyJJJKZdo8bsdWwkaB6`\nTo work the URL must be in this format of `https://open.spotify.com/track/<ID>`\n\n---------------------------------------------------------------------------------\n\nAxleBot also lets you queue your own Spotify and YouTube music playlists in the same way!\n\n__To queue and play a playlist__\n`-p <URL of YouTube playlist or Spotify Playlist>`\nE.g., `-p https://open.spotify.com/playlist/2utjwWZnVjfAv2Helpzz69` OR\n\nE.g., `-p https://www.youtube.com/watch?v=Uj1ykZWtPYI&list=PL9JM2aC37BG03vlqyhiYX54NG_thqqvbg`\n\n*Note: For this to work, the playlist should be public*\n\n**`-p` and `-play` are equivalent**\n--------------------------------------------------------------------------------",
                      colour=0x00b0f4)

    embed.set_author(name="AxleBot Help Commands")

    embed.add_field(name="Lyrics",
                    value="AxleBot lets you see the lyrics\nto a song (if it can be found).\n\n`-l` or `-lyrics` will display\nthe lyrics of the current \nplaying song",
                    inline=True)
    embed.add_field(name="Queue",
                    value="AxleBot uses a queue \nsystem to add songs.\nTo view the queue run\n`-q` or `-queue`",
                    inline=True)
    
    return embed

def craft_music_playback_controls_help_command():
    embed = discord.Embed(title="Music Playback Controls",
                      description="AxleBot supports all the usual normal playback controls *(with some new features coming later)*.",
                      colour=0x00b0f4)

    embed.set_author(name="AxleBot Help Commands")

    embed.add_field(name="Pause",
                    value="`-ps` or `-pause`\nWill pause the current \nplaying song",
                    inline=True)
    embed.add_field(name="Resume",
                    value="`-res` or `-resume`\nWill resume a paused song",
                    inline=True)
    embed.add_field(name="Skip",
                    value="`-skip` or `-skp`\nWill skip the current playing\nsong (if possible)",
                    inline=True)
    embed.add_field(name="Loop",
                    value="`-loop` or `-lp`\nWill toggle looping\nof the current playing song.\nIf on the song will be stuck on loop.\nRun `-loop` to toggle it off",
                    inline=True)
    embed.add_field(name="Repeat",
                    value="`-rep` or `-repeat`\nWill repeat the current playing song\nonce",
                    inline=True)
    embed.add_field(name="Play Next",
                    value="`-pn <any -p param>`\nWill take in anything `-p` \ncan play, and will queue it next up\n(right after the current song)",
                    inline=True)
    embed.add_field(name="Move song",
                    value="`-mv <position of song> <destination position>`\nWill select the song in the first position\nand move it to the second position\nE.g., `-mv 3 5` will move the 3rd song in the queue to the 5th position",
                    inline=True)
    embed.add_field(name="Delete",
                    value="`-del <position>`\nWill delete the song in\n`position` in the queue.\nE.g., `-del 5` will delete\nthe 5th song in the queue.",
                    inline=True)
    embed.add_field(name="Stop",
                    value="`-stop` or `stp`\nWill stop the music,\nclear the queue and\ndisconnect the bot",
                    inline=True)
    
    return embed

def craft_custom_playlist_help_command():
    embed = discord.Embed(title="Custom Playlist Commands",
                      description="AxleBot lets you create **your own custom playlists** and will save them for you. A custom playlist is a playlist of songs which you choose. Simply pick which songs you want to add and then we will store your music choice. **We will refer to \"custom playlists\" as just \"playlists\" for this help message**\n\n__To create a playlist__\n`-new_playlist <Name of Playlist>`\n\nAll the below aliases will also work:\n`\"np\", \"newplaylist\", \"newpl\", \"createplaylist\", \"createpl\", \"create_playlist\"`\n\nThis will bring up a message with instructions and a button to add songs. You must add YouTube or Spotify track URLs.\n\n__To add songs to playlist__\nIf you want to add more songs into a playlist you can run\n`-add_songs <Optional: Playlist name> <url 1> <url 2> <url 3> ...`\n\n*Note: If a playlist name is not provided the **last created playlist** will be chosen*\n\n__To queue/play a playlist__\nTo add all of a playlist's songs to the queue run:\n`-queue_playlist <Playlist name>`\n\nAll the below aliases will also work:\n`'qp', 'queuepl', 'queueplaylist', 'qpl', 'pp', 'playplaylist', 'playpl'`\n\n__To add the current playing song to a playlist__\nTo add **the current playing song** to a playlist run:\n`-add_song <Playlist name>`\n(`-addsong` will also work)\n\n__To delete a playlist__\n`-delete_playlist <Playlist name>`\n\nAll the below aliases will also work:\n`'dp', 'deletepl', 'deleteplaylist`",
                      colour=0x00b0f4)

    embed.set_author(name="AxleBot Help Commands")

    embed.add_field(name="See all playlists",
                    value="To see every playlist\n`-pls`\nThis will display the name of every\nplaylist you have created",
                    inline=True)
    embed.add_field(name="See playlist info",
                    value="To see the songs inside\na playlist run\n`-pls <Playlist name>`",
                    inline=True)
    embed.add_field(name="^",
                    value="For playlist info relatd commands (above two) these aliases will work\n`'playlists', 'playlist_info', 'playlistinfo'`",
                    inline=False)
    
    return embed


    
    
    

