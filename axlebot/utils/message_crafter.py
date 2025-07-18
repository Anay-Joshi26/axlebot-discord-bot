
"""
This file is the primary message crafter. It will craft discord Embeds to send out. To use it, find the function, and pass in any neccessary params
"""
import asyncio
import discord
from models.song import Song, LyricsStatus
from models.playlist import Playlist
from datetime import datetime
from utils import convert_duration
from discord.ui import View, Button
from math import ceil

# Colours for the embeds
COLOURS = {
    "error": 0xFF0000,
    "success": 0x00b0f4,
    "warning": 0xff9e42,
}

class QueuePaginator(View):
    def __init__(self, client, embeds: list[discord.Embed], timeout=24*60*60, starting_page = 0):
        super().__init__(timeout=timeout)
        self.embeds = embeds

        if starting_page < 0 or starting_page >= len(embeds):
            self.current_page = 0
        else:
            self.current_page = starting_page
        self.client = client

        self.client.live_queue_current_page = self.current_page
        self.page_indicator.label = self.get_page_info()
        self.update_buttons()

    def update_buttons(self):
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page == len(self.embeds) - 1
        self.first_page.disabled = self.current_page == 0
        self.last_page.disabled = self.current_page == len(self.embeds) - 1

    def get_page_info(self):
        return f"{self.current_page + 1}/{len(self.embeds)}"

    async def update_message(self, interaction: discord.Interaction):
        # Update button states
        self.update_buttons()
        self.page_indicator.label = self.get_page_info()
        self.client.live_queue_current_page = self.current_page
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.grey, row=0)
    async def first_page(self, interaction: discord.Interaction, button: Button):
        self.current_page = 0
        await self.update_message(interaction)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.blurple, row=0)
    async def prev_page(self, interaction: discord.Interaction, button: Button):
        self.current_page = max(0, self.current_page - 1)
        await self.update_message(interaction)

    @discord.ui.button(label="", style=discord.ButtonStyle.grey, disabled=True, row=0, custom_id="page_indicator")
    async def page_indicator(self, interaction: discord.Interaction, button: Button):
        pass  # Just a label, no action

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.blurple, row=0)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
        await self.update_message(interaction)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.grey, row=0)
    async def last_page(self, interaction: discord.Interaction, button: Button):
        self.current_page = len(self.embeds) - 1
        await self.update_message(interaction)


def craft_general_error(error: str = None) -> discord.Embed:
    """
    Creates an embed message to inform the user that an error has occured.
    If `error` is provided, it will be displayed in the embed.
    If `error` is not provided, a generic error message will be displayed.

    :param error: (Optional) The error message to display
    :return: A discord.Embed object
    """
    
    embed = discord.Embed(title="An error occurred",
                      description=f"{error if error else 'An *unknown* error occurred while processing your request'}",
                      colour=COLOURS["error"])
    
    return embed

async def craft_now_playing(song: Song, is_looping = False):
    embed = discord.Embed(
    title=(
        f"Now playing{' from YouTube Playlist' if song.is_playlist else ''}..." 
        if song.type == 'yt' 
        else f"Now playing from Spotify{' Playlist' if song.is_playlist else ''}..."
    ),
    #description=f"[{song.name}]({song.yt_url})", # uncomment this to make the song name a link to the song
    description=f"{song.name}",
    colour=await song.get_embed_color(),
    )
    
    embed.set_thumbnail(url=song.thumbnail_url)

    current_song_duration = song.duration

    # Add the progress bar field to the embed

    progress = calculate_progress(song)
    embed.add_field(name="Progress", value=update_progress_bar(progress), inline=True)

    embed.add_field(name="By", value=f"{song.artist}", inline=True)
    embed.add_field(
        name="Duration", value=convert_duration(current_song_duration), inline=True
    )
    #asyncio.create_task(update_progress_bar_embed(song, embed))
    return embed

def craft_playlist_added(type_of_playlist):
    embed = discord.Embed(title = f"{'Spotify' if type_of_playlist == 'spot' else 'YouTube'} Playlist Queued",
                    description=f"You have just queued a playlist.\n\nIt may take some time to queue every song in the playlist. *The songs are not guaranteed to show up in the original order*.\n\n**The first song should start to be queued shortly...**\n\nYou can inspect the queue to see the added songs via `-queue` or `q` (the songs will be added slowly).",
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
        update_interval = max(1, (song.duration/bar_length) * 0.4)

    print(f"Update interval: {update_interval} seconds")

    progress_bar: str = None # str
    interval_reduced = False

    while song.seconds_played < (song.duration - 2):
        #print("tick", song.name)
        if song.is_playing:
            progress = calculate_progress(song)
            new_progress_bar: str = update_progress_bar(progress, bar_length = bar_length)
            if progress_bar is None or new_progress_bar != progress_bar and song.progress_message:
                progress_embed.set_field_at(0, name="Progress", value=new_progress_bar)
                progress_embed.set_footer(text='🔂 Looped') if song.is_looping else progress_embed.set_footer(text='')
                await song.progress_message.edit(embed=progress_embed)
                progress_bar = new_progress_bar
        await asyncio.sleep(update_interval)

        if not song.is_first_in_queue:
            #asyncio.current_task().cancel()
            return
        #print(f"Progress: {progress}%")

        if song.is_playing and not interval_reduced:
            if progress > ((bar_length-2)/bar_length)*100:
                interval_reduced = True
                update_interval = max(1, update_interval * 0.5)  # Decrease the interval time to update more frequently as we approach the end of the song

    progress_embed.set_field_at(0, name="Progress", value=update_progress_bar(100, bar_length = bar_length))
    await song.progress_message.edit(embed=progress_embed)

def craft_delete_song(song: Song) -> discord.Embed:
    embed = discord.Embed(title=f"Deleted: {song.name}",
                      description="The song has been **deleted** from the queue, and will not be played.\n\nYou can view the updated queue via `-queue` or `-q`.",
                      colour=0x00b0f4)

    #embed.set_author(name=song.artist)

    embed.set_thumbnail(url=song.thumbnail_url)

    return embed

def craft_move_song(song: Song, move_to: int) -> discord.Embed:
    embed = discord.Embed(title=f"Moved: {song.name}",
                      description=f"The song has been **moved** to position `{move_to}` in the queue.\n\nYou can view the updated queue via `-queue` or `-q`.",
                      colour=0x00b0f4)
    embed.set_thumbnail(url=song.thumbnail_url)
    return embed


def update_progress_bar(progress, bar_length=18):
    filled_length = int(bar_length * progress / 100)
    empty_length = bar_length - filled_length
    bar = "█" * filled_length + "░" * empty_length
    return f"{bar}"

def calculate_progress(song):
    progress = (song.seconds_played / song.duration) * 100
    return min(progress, 100)  # Ensure progress doesn't exceed 100%

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
            description="No lyrics were found for this song with that title and artist",
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

def craft_queue_empty(live = False):
    embed = discord.Embed(
        title=f"The song queue is empty! {'[LIVE]' if live else ''}",
        description=f"The queue is empty use `-p [song_name]` to play and add songs to the queue\n\n*AxleBot will leave the voice channel after 3 minutes of inactivity*",
        colour=0x00b0f4)
    return embed

def craft_queue(client, num = None, live: bool = False, starting_page = 0):
    queue = client.queue
    if len(queue) == 0:
        embed = craft_queue_empty(live=live)
        return [embed], None  # Return single embed, no paginator
    
    MAX_PER_PAGE = 20  # You can change this

    nums_to_show = min(num if num is not None else len(queue), len(queue))

    embeds = []
    for page_num in range(ceil(nums_to_show / MAX_PER_PAGE)):
        start = page_num * MAX_PER_PAGE
        end = min(start + MAX_PER_PAGE, nums_to_show)
        opt = ""

        for i in range(start, end):
            if i == 0:
                opt += f"[{i+1}] **{queue[i].name}** => Now playing...{' [LOOPED]' if queue.loop_current else ''}\n"
            else:
                opt += f"[{i+1}] **{queue[i].name}**\n"

        # Only on the last page, add autoplay queue if needed
        if page_num == ceil(nums_to_show / MAX_PER_PAGE) - 1:
            autoplay_queue = getattr(queue, "auto_play_queue", [])
            if len(queue) <= 10 and autoplay_queue:
                opt += "\n====================================\n"
                opt += "**Autoplay is enabled. These tracks will play after the queue ends:**\n\n"
                for i, track in enumerate(autoplay_queue, start=1):
                    opt += f"[A{i}] {track.name}\n"

        title_suffix = f" (first {num})" if num is not None and num < len(queue) and num > 0 else ""
        embed = discord.Embed(
            title=f"Queue of Songs{title_suffix} {'[LIVE]' if live else ''}",
            description=opt,
            colour=0x00b0f4,
        )
        embed.set_footer(text=f"Page {page_num+1}")
        embeds.append(embed)

    paginator = QueuePaginator(client, embeds=embeds, starting_page=starting_page)  
    return embeds, paginator


def craft_playlist_created(name: str) -> discord.Embed:

    embed = discord.Embed(title=f"{name}",
                      description=f"A playlist named `{name}` has been created and currently has `0` songs inside it. \n\nTo add your own songs you use the command:\n\n`-add_songs \"<Playlist name>\" <url 1> <url 2> \"<Song name>\" ...`\n\n OR\n\n Use the button below to add songs to this newly created playlist\n\nYou can add up to 30 songs in one playlist, if you enter more than 30 songs only the first 30 will be added.\n\nThe urls can be YouTube links or Spotify links (to individual songs), they **cannot** be Spotify or YouTube Playlist links.",
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
        title=f"Songs successfully added to `{name}`",
        description=f"The following songs were successfully added:\n\n{songs_description}",
        colour=COLOURS["success"]
    )

    if len(songs_added) == 1:
        embed.set_thumbnail(url=songs_added[0].thumbnail_url)
    
    return embed

def craft_custom_playlist_queued(name: str, playlist: Playlist, shuffle = False) -> discord.Embed:
    embed = discord.Embed(
        title=f'{name} - Playlist Queued',
        description=f"A custom playlist has been queued{' in a shuffled order' if shuffle else ''}. \n\nEvery song inside the playlist has been added to the queue:\n\n",
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
        description=f'The playlist named `{name}` has been successfully deleted',
        colour=COLOURS["success"]
    )
    
    return embed

def craft_song_deleted_from_playlist(name: str, song: Song) -> discord.Embed:
    """
    Creates an embed message to show that a song has been deleted from a playlist.

    :param name: The name of the playlist
    :param song_name: The name of the song that was deleted

    :return: A discord.Embed object
    """
    
    embed = discord.Embed(
        title=f"{song.name} deleted from {name}",
        description=f'The song named **{song.name}** has been successfully deleted from **{name}**',
        colour=COLOURS["success"]
    )

    embed.set_thumbnail(url=song.thumbnail_url)
    
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
        description=f"The following queries could not be converted into songs:\n\n{urls_description}",
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
    description = "\n".join([f"{i+1}. {playlist.name}" for i, playlist in enumerate(playlists)])

    header = f"The server currently has `{n}` playlists"
    middle = f", they are:\n\n{description}\n\n" if n != 0 else ".\n\n"
    footer = f"Run `-playlists <Playlist Name>` to see the songs for a particular playlist" if n > 0 else "Run `-new_playlist <Playlist Name>` to create a new playlist"

    embed = discord.Embed(
        title="All Playlists",
        description=header + middle + footer,
        colour=COLOURS["success"]
    )

    return embed


def craft_songs_in_playlist(playlist) -> discord.Embed:
    """
    Creates an embed message to show all the songs in a playlist.

    :param playlist_name: The name of the playlist

    :param songs: A list of song names

    :return: A discord.Embed object
    """
    playlist_name = playlist.name
    songs = playlist.songs

    n = len(songs)

    description = "\n".join([f"{i+1}. {song.name}" for i,song in enumerate(songs)])

    embed = discord.Embed(title=f"Songs in `{playlist_name}`",
                      description=f"The playlist named `{playlist_name}` currently has `{n}` songs{', they are:' if n != 0 else '.'}\n\n{description}",
                      colour=0x00b0f4)

    embed.add_field(name="Total Songs", value=f"{len(songs)}", inline=True)
    embed.add_field(name="Total Duration", value=convert_duration(playlist.total_duration), inline=True)
    embed.add_field(name="Playlist Created At", value=datetime.fromtimestamp(playlist.created_at).strftime('%d/%m/%Y %H:%M'), inline=True)

    return embed

def craft_default_help_command():
    embed = discord.Embed(title="Help commands",
                      description="AxleBot can do many things, scroll through and select the option which you would like to see the help commands for.\n\n**Message spamming**\nEvery command has a cooldown to prevent spamming. " \
                      "This is `3` seconds per command for the whole server. This `-help` command has a `1` second cooldown.\n\n**Other things to note**\nThe bot keeps some persistent info about a server such as playlists created. Sometimes this info can take a few seconds to retrieve if you have been inactive for a while. " \
                      "\n\n**For Admins**\nFor admins with Manage Server permissions, you can configure the bot to only work in certain channels and with certain roles. Run `-help admin` to see how to do that.",
                      colour=0x00b0f4)

    embed.set_author(name="AxleBot Help Commands")

    return embed

def craft_playing_music_help_command():

    embed = discord.Embed(title="Playing Music",
                      description="AxleBot at its core a powerful music bot which supports music playback from YouTube and Spotify. If auto play is enabled in your server songs will continue to play via Spotify's recommendation algorithm.\n\n__To play a song **with a query**__\n`-p <Query>`\nE.g.,  `-p rick roll`\n\n__To play a song **with a YouTube URL**__\n`-p <YouTube URL>` \nE.g., `-p https://www.youtube.com/watch?v=dQw4w9WgXcQ`\nTo work the URL must be in this format of `https://www.youtube.com/watch?v=<ID>`\n\n__To play a song **with a Spotify Track URL**__\n`-p <Spotify Track URL>` \nE.g., `-p https://open.spotify.com/track/7ixxyJJJKZdo8bsdWwkaB6`\nTo work the URL must be in this format of `https://open.spotify.com/track/<ID>`\n\n---------------------------------------------------------------------------------\n\nAxleBot also lets you queue your own Spotify and YouTube music playlists (and albums) in the same way!\n\n__To queue and play a playlist__\n`-p <URL of YouTube playlist or Spotify Playlist>`\nE.g., `-p https://open.spotify.com/playlist/2utjwWZnVjfAv2Helpzz69` OR\n\nE.g., `-p https://www.youtube.com/watch?v=Uj1ykZWtPYI&list=PL9JM2aC37BG03vlqyhiYX54NG_thqqvbg`\n\n*Note: For this to work, the playlist should be public*\n\n**`-p` and `-play` are equivalent**\n--------------------------------------------------------------------------------",
                      colour=0x00b0f4)

    embed.set_author(name="AxleBot Help Commands")

    embed.add_field(name="Lyrics",
                    value="AxleBot lets you see the lyrics\nto a song (if it can be found).\n\n`-l` or `-lyrics` will display\nthe lyrics of the current \nplaying song",
                    inline=True)
    embed.add_field(name="Queue",
                    value="AxleBot uses a queue \nsystem to add songs.\nTo view the queue run\n`-q` or `-queue`.\nYou can add a `-live` at the end to see the queue in real-time\n(e.g., `-q -live`)",
                    inline=True)
    embed.add_field(name="Now Playing",
                    value="To see the song playing right now \n run `-nowplaying`",
                    inline=True)
    
    return embed

def craft_music_playback_controls_help_command():
    embed = discord.Embed(title="Music Playback Controls",
                      description="AxleBot supports all the usual normal playback controls. Some of these can be clicked via buttons in the music playback message, but you can also run the commands in the chat.",
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
                    value="`-loop` or `-lp`\nWill toggle looping\nof the current playing song.\nIf on the song will be stuck on loop.\nRun `-loop` again to toggle it off",
                    inline=True)
    embed.add_field(name="Repeat",
                    value="`-rep <Optional: num>` or `-repeat`\nWill repeat the current playing song\n`num` times.\nIf no number is provided it will repeat the song once.\nAdding a `q` or `-q` at the end or similar will repeat the entire queue\nE.g., `-rep 3 -q` will repeat the queue 3 times",
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

def craft_music_playback_controls_help_command_page_2():
    embed = discord.Embed(title="Music Playback Controls (cont.)",
                      description="",
                      colour=0x00b0f4)

    embed.set_author(name="AxleBot Help Commands")

    embed.add_field(name="Shuffle",
                    value="`-sh` or `-shuffle`\nWill shuffle the current queue\nand play the songs in a random order",
                    inline=True)
    embed.add_field(name="Seek",
                    value="`-seek <seconds or timestamp>`\nWill seek the current playing song to\n`seconds` or `timestamp` into the song.\nE.g., `-seek 30` will seek to 30 seconds in the song\nE.g., `-seek 01:30` will seek to 1 minute and 30 seconds in the song",
                    inline=True)
    embed.add_field(name="Rewind",
                    value="`-rewind <seconds>`\nWill rewind the current playing song by\n`seconds` seconds.\nE.g., `-rewind 10` will rewind the song by 10 seconds",
                    inline=True)
    embed.add_field(name="Forward",
                    value="`-forward <seconds>`\nWill forward the current playing song by\n`seconds` seconds.\nE.g., `-forward 10` will forward the song by 10 seconds",
                    inline=True)
    
    return embed

def craft_music_filters_help_command():
    desc = """
            Music filters modify the audio that's currently playing — things like speeding it up, boosting bass, adding vibrato, or rotating the stereo channels. AxleBot supports several filters you can apply to enhance your listening experience.

            ---

            **Available Filters and Their Values:**

            - `timescale_speed` — Playback speed multiplier without pitch change  
            (e.g., `1.0` = normal, `1.5` = 50% faster, `0.75` = 25% slower)

            - `timescale_pitch` — Pitch multiplier  
            (e.g., `1.0` = normal pitch, `1.2` = higher, `0.8` = lower)

            - `timescale_rate` — Playback rate multiplier (changes speed *with* pitch)  
            (e.g., `1.0` = normal, `1.3` = faster and higher-pitched)

            - `vibrato_depth` — Depth of vibrato effect  
            (`0.0` to `1.0` — how much the pitch wobbles)

            - `vibrato_frequency` — Frequency of vibrato (in Hz)  
            (e.g., `4.0` = faster vibrato)

            - `bassboost` — Amount of bass boost  
            (`0.0` to `1.0`, higher = stronger bass)

            - `rotation` — Rotates audio across stereo channels giving the 8D audio effect
            (e.g., `0.1` = slow circular motion, `3.0` = very fast)

            - `karaoke_level` — Attempts to remove vocals by filtering center frequencies (simulating the karaoke effect)
            (`0.0` to `1.0`, higher = stronger vocal reduction)

            ---

            **How to Apply Filters:**

            Use the `-set_filters` or `-sf` command followed by one or more filters and their values.

            Format:  
            `-set_filters -filter_name value -filter_name value ...`

            Example:  
            `-set_filters -timescale_speed 1.2 -bassboost 0.6 -rotation 0.3`

            This will speed up playback, add bass, and rotate audio in stereo to give the 8D effect.

            Each `-set_filters` command will overwrite any previous filters set. Ensure that you combine required filters in one command.

            ---

            **How to Clear Filters:**

            To remove all filters and return to normal playback, use:  
            `-clear_filters` or `-cf`

            This will reset all audio effects and playback settings to their defaults. 

            *Note: Applying and clearing filters can take a few seconds to process, so please be patient.*
            """


    embed = discord.Embed(title="Music Filters",
                      description=desc,
                      colour=0x00b0f4)

    embed.set_author(name="AxleBot Help Commands")
    
    return embed


def craft_custom_playlist_help_command():
    # embed = discord.Embed(title="Custom Playlist Commands",
    #                   description="AxleBot lets you create **your own custom playlists** and will save them for you. A custom playlist is a playlist of songs which you choose. Simply pick which songs you want to add and then we will store your music choice. **We will refer to \"custom playlists\" as just \"playlists\" for this help message**\n\nYou can create up to **10** playlists, each can have a max of **30** songs within it\n\n__To create a playlist__\n`-new_playlist <Name of Playlist>`\n\nAll the below aliases will also work:\n`\"np\", \"newplaylist\", \"newpl\", \"createplaylist\", \"createpl\", \"create_playlist\"`\n\nThis will bring up a message with instructions and a button to add songs. You can add YouTube or Spotify track URLs or just type a query for the song name.\n\n__To add songs to playlist__\nIf you want to add more songs into a playlist you can run\n`-add_songs \"<Playlist name>\" <url 1> <url 2> \"<Song name>\" ...`\nThe playlist name should be wrapped in double quotes. If you enter a song name which is **not** a URL wrap the name in double quotes also.\n\n__To queue/play a playlist__\nTo add all of a playlist's songs to the queue run:\n`-queue_playlist <Playlist name>`\n\nAll the below aliases will also work:\n`'qp', 'queuepl', 'queueplaylist', 'qpl', 'pp', 'playplaylist', 'playpl'`\n\n__To add the current playing song to a playlist__\nTo add **the current playing song** to a playlist run:\n`-add_song <Playlist name>`\n(`-addsong` will also work)\n\n__To delete a playlist__\n`-delete_playlist <Playlist name>`\n\nAll the below aliases will also work:\n`'dp', 'deletepl', 'deleteplaylist`",
    #                   colour=0x00b0f4)
    embed = discord.Embed(
    title="Custom Playlist Commands",
    description=(
        "AxleBot lets you create **your own custom playlists** and will save them for you. A custom playlist is a playlist of songs which you choose. "
        "Simply pick which songs you want to add and we'll store your music choices. "
        "**We will refer to \"custom playlists\" as just \"playlists\" for this help message.**\n\n"

        "You can create up to **10** playlists, and each can have a maximum of **30** songs.\n\n"

        "__To create a playlist__\n"
        "`-new_playlist <Name of Playlist>`\n"
        "Aliases: `np`, `newplaylist`, `newpl`, `createplaylist`, `createpl`, `create_playlist`\n\n"
        "This will bring up a message with instructions and a button to add songs. "
        "You can add YouTube or Spotify track URLs, or just type a query for the song name.\n\n"

        "__To add songs to a playlist__\n"
        "Run `-add_songs` and then provide the playlist name and the songs you want to add. OR\n"
        "`-add_songs \"<Playlist name>\" <url 1> <url 2> \"<Song name>\" ...`\n"
        "Wrap the playlist name in double quotes. If the song is **not** a URL, wrap the name in double quotes as well.\n\n"

        "__To queue/play a playlist__\n"
        "`-queue_playlist <Playlist name> <-s : Optional to shuffle>`\n"
        "Aliases: `qp`, `queuepl`, `queueplaylist`, `qpl`, `pp`, `playplaylist`, `playpl`, `queue_pl`*\n\n"

        "__To add the current playing song to a playlist__\n"
        "`-add_song <Playlist name>` (`-addsong` also works)\n\n"

        "__To delete a playlist__\n"
        "`-delete_playlist <Playlist name>`\n"
        "Aliases: `dp`, `deletepl`, `deleteplaylist`"
        ),
        colour=0x00b0f4
    )


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

def craft_custom_playlist_help_command_page_2():
    embed = discord.Embed(
        title="Custom Playlist Commands (cont.)",
        description=(
            "__Delete a song from a playlist__\n"
            "`-del_from_pl \"<Playlist name>\" \"<position or song name>\"`\n"
            "e.g. `-del_from_pl \"Test\" \"3\"` would **delete the third song** from a playlist named \"Test\"\n"
            "e.g. `-del_from_pl \"Test\" \"Rick Roll\"` would **delete the song named 'Rick Roll'** from the playlist\n"
            "*Note: Use double quotes around names and positions to avoid formatting issues*"
            "\n\n"
            "__Rename playlist__\n"
            "`-rename_pl \"<Old Name>\" \"<New Name>\"`\n"
            "e.g. `-rename_pl \"Test\" \"New Test\"` will rename a playlist to \"New Test\" from \"Test\""
        )
    )

    return embed


def craft_playlist_renamed(old_name: str, new_name: str) -> discord.Embed:
    """
    Creates an embed message to show that a playlist has been renamed.

    :param old_name: The old name of the playlist
    :param new_name: The new name of the playlist

    :return: A discord.Embed object
    """
    
    embed = discord.Embed(
        title=f"Playlist renamed",
        description=f'The playlist named "{old_name}" has been successfully renamed to "{new_name}"',
        colour=COLOURS["success"]
    )
    
    return embed

def craft_admin_help_command():
    description = """
    AxleBot has some admin commands which can be used to manage the bot and its settings. Any user which has the 'Manage Guild' permission will be able to use these commands.

    Out of the box AxleBot will work in any text channel named "music" (if the server has one). Aside from that, it will work in **no other** text channels. Initally only users with the **Manage Server** permission will be able to use the bot. A maximum of `10` roles and `10` text channels can be configured to have access to the bot.

    You can configure the bot to work in any text channel and with any role you want. This is done by using the commands below.
    """
    embed = discord.Embed(title="AxleBot Admin Commands",
                      description=description,
                      colour=0x00b0f4,
                      timestamp=datetime.now())

    embed.add_field(name="Add role",
                    value="To add a role which can \nexecute music commands run:\n`-add_use_role @Role1 @Role2 ...` \n*Note: You can use @everyone here aswell*",
                    inline=True)
    embed.add_field(name="Remove role",
                    value="To disallow a role to use music\ncommands run:\n`-remove_use_role @Role1 @Role2 ...`\n*Note: You can use @everyone here aswell*",
                    inline=True)
    embed.add_field(name="See all access roles",
                    value="To see all roles which have\naccess to music commands run:\n`-see_access_roles`",
                    inline=True)
    embed.add_field(name="Add channel",
                    value="To add a channel which can \nexecute music commands run:\n`-add_use_channel #text-channel1 #text-channel2 ...`",
                    inline=True)
    embed.add_field(name="Remove channel",
                    value="To disallow a channel to use music\ncommands run:\n`-remove_use_channel #text-channel1 #text-channel2 ...`",
                    inline=True)
    embed.add_field(name="See all access channels",
                    value="To see all channels which have access to music commands run:\n`-see_access_channels`",
                    inline=True)
    embed.add_field(name="Delete message after playing",
                    value="To delete song message after \nplaying run:\n`-delete_message_after_play \n<true or false>`\n*This can help to de-clutter song\nmessages*\n\nAliases: `del_message_after_play`, `del_msg_after_play`, `dmap`",
                    inline=True)
    embed.add_field(name="Auto play songs",
                    value="To enable or disable auto play run:\n`-autoplay <true or false>`\n*Auto play will automatically queue songs based on the current queue using Spotify's recommendation algorithm*\n\nAliases: `autoplay`, `ap`",
                    inline=True)
    embed.add_field(name="See all config",
                    value="To see the bots entire configuration run:\n`-see_all_config` or `-sac`",
                    inline=True)

    embed.set_footer(text="This information has been sent to you privately")

    return embed

def craft_see_access_embed(access_type: str, entities: list[str]) -> discord.Embed:
    """
    Creates an embed listing the configured roles or channels for bot access.

    Parameters:
    - access_type (str): Either "role" or "channel".
    - entities (list[str]): A list of role/channel names.

    Returns:
    - discord.Embed: The generated embed object.
    """
    title = f"Configured {access_type.capitalize()}s"

    if not entities:
        if access_type == "role":
            description = (
                "No roles are currently configured. The bot will only work for users "
                "with the **Manage Server** permission."
            )
        elif access_type == "channel":
            description = (
                "No channels are currently configured. The bot will not work in any channel."
            )
    else:
        description = "\n".join(f"{i+1}. {name}" for i, name in enumerate(entities))
        if access_type == "role":
            description += "\n\n*Note: Those with 'Manage Server' permissions will also be able to use the bot*"

    return discord.Embed(
        title=title,
        description=description,
        color=COLOURS["success"]
    )

def craft_update_access_embed(access_type: str, entities: list[str], action: str, added: bool = True) -> discord.Embed:
    access_type_title = access_type.capitalize()
    action_title = "Add" if action == "add" else "Remove"

    if added:
        title = f"{action_title}ed {access_type_title} Access"
        if not entities:
            description = f"No {access_type}s were {action}ed."
        else:
            description = "\n".join(f"{i+1}. `{entity}`" for i, entity in enumerate(entities))
        color = COLOURS["success"]
    else:
        title = f"Failed to {action_title} {access_type_title} Access"
        if not entities:
            description = f"No {access_type}s were provided."
        else:
            description = f"An error occurred while trying to {action} the following {access_type}(s):\n" + \
                          "\n".join(f"{i+1}. `{entity}`" for i, entity in enumerate(entities))
        color = COLOURS["error"]  # You can replace this with `discord.Color.red()` if needed

    embed = discord.Embed(title=title, description=description, color=color)
    return embed

    

