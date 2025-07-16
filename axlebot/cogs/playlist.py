import discord
from discord.ext import commands
from core.commands_handler import audio_command_check, in_voice_channel, cooldown_time, bot_use_permissions
from music.song_request_handler import determine_query_type, convert_to_standard_youtube_url
from models.song import Song, LyricsStatus
import asyncio
from utils.message_crafter import *
from core.server_manager import ServerManager
from models.client import Client
from music.songs_queue import SongQueue
from models.playlist import Playlist
from cogs.music import MusicCog
from discord.ext.commands import BucketType
from copy import deepcopy
import random
from core.lavalink import LavalinkVoiceClient

class CreatePlaylistModal(discord.ui.Modal):

    def __init__(self, name, ctx: commands.Context, title = 'Create a Playlist'):
        super().__init__(timeout = 300, title=title)
        self.playlist_name: str = name
        self.ctx = ctx
        self.name_input = discord.ui.TextInput(label='Playlist Name', style=discord.TextStyle.short, default=self.playlist_name, required=True)
        self.song_links_input = discord.ui.TextInput(label='Songs', required=False, style=discord.TextStyle.paragraph, placeholder="https://www.youtube.com/watch?v=video_id\nhttps://open.spotify.com/track/track_id\nRick Roll\n...")

        self.add_item(self.name_input)
        self.add_item(self.song_links_input)

    async def on_submit(self, interaction: discord.Interaction):

        playlist_name = self.name_input.value
        song_links = self.song_links_input.value.split("\n")

        if len(song_links) == 0:
            await interaction.response.send_message("You didn't provide any songs to add", ephemeral=True)
            return

        await interaction.response.send_message("Adding songs to the playlist...", ephemeral=True)

        playlist_cog : PlaylistCog = self.ctx.bot.get_cog('PlaylistCog')

        if playlist_cog:
            await playlist_cog.add_songs_to_playlist(playlist_name=playlist_name, urls=song_links, ctx=self.ctx)

        #await PlaylistCog.add_songs_to_playlist(playlist_name=playlist_name, urls = song_links, ctx=self.ctx)

class AddSongsButton(discord.ui.View):
    def __init__(self, name, ctx, title = None):
        super().__init__()
        self.name = name
        self.ctx = ctx
        self.title = 'Create a Playlist' if title is None else title

    @discord.ui.button(style=discord.ButtonStyle.success, label='Add Songs')
    async def add_songs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreatePlaylistModal(self.name, self.ctx, self.title))



class PlaylistCog(commands.Cog):
    """
    This cog is responsible for handling all custom playlist related commands.

    A custom playlist is one that is created by the user, and is populated with their chosen music. They can choose to
    add songs from YouTube or Spotify and can play this custom playlist whenever they want.
    """
    def __init__(self, bot: commands.Bot, server_manager):
        self.bot = bot
        self.server_manager : ServerManager = server_manager
        self.YT_SONG, self.SPOT_SONG, self.YT_PLAYLIST, self.SPOT_PLAYLIST, self.STD_YT_QUERY = range(5)
        self.music_cog : MusicCog = self.bot.get_cog('MusicCog')

    @commands.command(aliases = ['np', "newplaylist", "newpl", "createplaylist", "createpl", "create_playlist"])
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def new_playlist(self, ctx: commands.Context, *args):
        """
        Creates a new playlist with the given name.
        """
        if not args:
            await ctx.send("You didn't provide a name for the playlist!")
            return
        
        name = " ".join(args)
        client = await self.server_manager.get_client(ctx.guild.id, ctx)
        playlist = Playlist(name, ctx.guild.id)

        print("Playlist created")

        try:
            await client.add_playlist(playlist)
        except ValueError as e:
            await ctx.send(str(e))
            return
        
        embed = craft_playlist_created(name)

        await ctx.send(embed = embed, view=AddSongsButton(name, ctx))


    async def add_songs_to_playlist(self, playlist_name: str | None, urls: list[str], ctx: commands.Context, client: Client | None = None, playlist: Playlist | None = None):
        """
        Adds songs to the playlist from the given list of urls, with up to 5 processed concurrently.
        """
        if not client:
            client = await self.server_manager.get_client(ctx.guild.id, ctx)

        if not playlist:
            if playlist_name is not None:
                playlist = client.get_playlist_by_name(playlist_name)
            else:
                raise ValueError("Invalid params passed to add_songs_to_playlist()")

        if not playlist:
            pl_not_found = craft_no_playlist_found(playlist_name)
            await ctx.send(embed=pl_not_found)
            return

        added_songs = []
        error_songs = []
        semaphore = asyncio.Semaphore(2) # Limit concurrent processing

        adding_songs_msg = await ctx.send("Adding songs...", silent=True)
        limit_reached = False

        async def process_url(url: str):
            nonlocal limit_reached
            async with semaphore:
                type_of_query = determine_query_type(url)
                if type_of_query == self.YT_SONG:
                    url = convert_to_standard_youtube_url(url)
                    song = await Song.SongFromYouTubeURL(url)
                elif type_of_query == self.SPOT_SONG:
                    song = await Song.SongFromSpotifyURL(url)
                elif type_of_query == self.STD_YT_QUERY:
                    song = await Song.CreateSong(url)
                else:
                    error_songs.append(url)
                    return

                if song is None:
                    error_songs.append(url)
                    return

                try:
                    playlist.add_song(song)
                    added_songs.append(song)
                except ValueError as e:
                    limit_reached = True
                    print(f"SONG LIMIT REACHED (guild_id: {ctx.guild.id}): e: [{e}]")
                    raise ValueError("Stopped adding songs due to error") from e

        try:
            async with asyncio.TaskGroup() as tg:
                for url in urls:
                    tg.create_task(process_url(url))
            #await asyncio.gather(*(process_url(url) for url in urls))
        except Exception:
            pass

        if added_songs:
            songs_added_embed = craft_songs_added_to_playlist(playlist.name, added_songs)
            await ctx.send(embed=songs_added_embed)
            await client.update_playlist_changes_db()

        if limit_reached:
            await ctx.send("No more songs will be added to the playlist\nYou have reached the maximum number of songs allowed in a playlist.")

        await adding_songs_msg.delete()

        if error_songs:
            error_urls_embed = craft_songs_not_added(error_songs)
            await ctx.send(embed=error_urls_embed)

    @commands.command(aliases = ['as', 'addsongs'])
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def add_songs(self, ctx: commands.Context, *args):

        client = await self.server_manager.get_client(ctx.guild.id, ctx)

        if not args:
            await ctx.send("You can use the button below to add songs to a playlist of your choice", view=AddSongsButton(None, ctx, title = "Add songs to a playlist"))
            #await ctx.send("You didn't provide any songs to add", silent = True)
            return
        
        playlist_name = args[0]; 
        urls = args[1:]

        playlist = client.get_playlist_by_name(playlist_name)

        if playlist is None:
            no_pl_found = craft_no_playlist_found(playlist_name)
            await ctx.send(embed = no_pl_found)
            return
                
        try:
            await self.add_songs_to_playlist(playlist_name, urls, ctx, client = client) 
        except ValueError as e:
            await ctx.send(str(e))

    @commands.command(aliases = ['addsong'])
    @commands.check(in_voice_channel)
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def add_song(self, ctx: commands.Context, *, playlist_name) -> None:
        """
        Adds the current playing to a playlist with the given name.
        """
        if not playlist_name:
            await ctx.send("You didn't provide a playlist name")
            return

        client = await self.server_manager.get_client(ctx.guild.id, ctx)
        queue, voice_client = client.queue, client.voice_client

        if len(queue) == 0 or voice_client is None:
            await ctx.send("No song is currently playing", silent = True)
            return
        
        playlist = client.get_playlist_by_name(playlist_name)

        if not playlist:
            no_pl_found = craft_no_playlist_found(playlist_name)
            await ctx.send(embed = no_pl_found)
            return
        
        current_song = queue.current_song

        try:
            playlist.add_song(current_song)
        except ValueError as e:
            await ctx.send(embed = craft_general_error(str(e)))
            return

        await client.update_playlist_changes_db()

        song_added_embed = craft_songs_added_to_playlist(playlist.name, [current_song])
        await ctx.send(embed = song_added_embed)
    
    @commands.command(aliases = ['qp', 'queuepl', 'queueplaylist', 'qpl', 'pp', 'playplaylist', 'playpl', 'queue_pl'])
    @commands.check(in_voice_channel)
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def queue_playlist(self, ctx: commands.Context, *args):
        """
        Queues the playlist with the given name.
        """
        try:
            if not args:
                await ctx.send("You didn't provide a playlist name")
                return
            shuffle = False
            if args[-1] == "-s" or args[-1] == "--shuffle" or args[-1] == "-sh" or args[-1] == "-shuffle" \
                or args[-1] == "--shuffled" or args[-1] == "-shuffled":
                shuffle = True
                print("Shuffling playlist before playing")

            name = " ".join(args[:-1]) if shuffle else " ".join(args)
            client = await self.server_manager.get_client(ctx.guild.id, ctx)
            playlist = client.get_playlist_by_name(name)

            if not playlist:
                no_pl_found = craft_no_playlist_found(name)
                await ctx.send(embed = no_pl_found)
                return

            if client.voice_client is None:
                vc = await ctx.author.voice.channel.connect(cls = LavalinkVoiceClient)
                client.voice_client = vc

            queue = client.queue

            playlist = deepcopy(playlist)

            if shuffle:
                random.shuffle(playlist.songs)

            pl_added = craft_custom_playlist_queued(name, playlist, shuffle=shuffle)

            await ctx.send(embed = pl_added)
            auto_play_updated = False

            for song in playlist.songs:
                await queue.append(song, update_auto_play = False)

                if len(queue) == 5:
                    auto_play_updated = True
                    await client.queue.update_auto_play_songs()

                if len(queue) == 1:
                    song.is_first_in_queue = True
                    await self.music_cog.send_play_song_embed(ctx, song, client)

                    player = await song.player

                    if player is None:
                        await ctx.send(embed=craft_general_error(f"YouTube has temporarily blocked `{song.name}` :(, please try again later"), delete_after = 20)
                        # asyncio.create_task(self.music_cog.play_next(ctx, client))
                        # return
                    else:
                        await client.voice_client.play(
                            player,
                            after = lambda e: self.bot.loop.call_soon_threadsafe(
                                            lambda: asyncio.ensure_future(self.music_cog._after_playback(e, ctx, client)))
                        )
            if not auto_play_updated and client.server_config.auto_play:
                # If auto play is enabled, update the auto play songs
                await client.queue.update_auto_play_songs()
        except Exception as e:
            print(f"Error in queue playlist command: {e}")
            await ctx.send(embed=craft_general_error(), delete_after = 20)

    @commands.command(aliases = ['pls', 'playlist_info', 'playlistinfo'])
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def playlists(self, ctx: commands.Context, *args):
        """
        Lists all the playlists created by the user
        """
        client = await self.server_manager.get_client(ctx.guild.id, ctx)

        # if len(client.playlists) == 0:
        #     await ctx.send("You haven't created any playlists yet")
        #     return
        
        if args:
            playlist_name = " ".join(args)
            playlist = client.get_playlist_by_name(playlist_name)

            if not playlist:
                no_pl_found = craft_no_playlist_found(playlist_name)
                await ctx.send(embed = no_pl_found)
                return
            
            playlist_embed = craft_songs_in_playlist(playlist)
            await ctx.send(embed = playlist_embed)

        else:
            all_playlists_embed = craft_view_all_playlists(client.playlists)
            await ctx.send(embed = all_playlists_embed)

    
    @commands.command(aliases = ['dp', 'deletepl', 'deleteplaylist'])
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def delete_playlist(self, ctx: commands.Context, *args):
        """
        Deletes the playlist with the given name
        """
        if not args:
            await ctx.send("You didn't provide a playlist name")
            return
        
        name = " ".join(args)
        client = await self.server_manager.get_client(ctx.guild.id, ctx)
        playlist = client.get_playlist_by_name(name)

        if not playlist:
            no_pl_found = craft_no_playlist_found(name)
            await ctx.send(embed = no_pl_found)
            return
        
        client.remove_playlist_by_playlist(playlist)

        await client.update_playlist_changes_db()

        pl_deleted = craft_playlist_deleted(name)
        await ctx.send(embed = pl_deleted)


        
    @commands.command(aliases = ['remove_song', 'removesong', 'rs', "del_from_playlist","deletefromplaylist", "dfp", "del_from_pl"])
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def delete_song_from_playlist(self, ctx: commands.Context, *args):
        """
        Deletes the song at the given position from the playlist with the given name
        """
        if not args:
            await ctx.send("You didn't provide a playlist name and song index")
            return
        
        name = " ".join(args[:-1])
        index = args[-1]

        client = await self.server_manager.get_client(ctx.guild.id, ctx)
        playlist = client.get_playlist_by_name(name)

        if not playlist:
            no_pl_found = craft_no_playlist_found(name)
            await ctx.send(embed = no_pl_found)
            return
        
        # Try to interpret index as an integer position
        try:
            position = int(index)
            if position < 1 or position > len(playlist.songs):
                await ctx.send(f"Position `{position}` is out of range. Please provide a valid position between 1 and {len(playlist.songs)}")
                return
            song = playlist.remove_song(position - 1)

        except ValueError:
            # If index is not an integer, try treating it as a song name
            song_idx = playlist.get_song(index, return_index = True)
            if song_idx is None:
                await ctx.send(f"Could not find a song with the name `{index}` in the playlist.")
                return
            song = playlist.remove_song(song_idx)


        await client.update_playlist_changes_db()

        song_deleted = craft_song_deleted_from_playlist(name, song)
        await ctx.send(embed = song_deleted)

    @commands.command(aliases = ["renameplaylist", "renamepl", "rename_pl"])
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def rename_playlist(self, ctx: commands.Context, *args):
        """
        `-rename_pl "<Old Name>" "<New Name>"`

        e.g `-rename_pl "Test" "New Test"` will rename a playlist to "New Test" from "Test"
        """
        if len(args) < 2:
            await ctx.send("You didn't provide a playlist name and a new name")
            return
        
        old_name = args[0]
        new_name = " ".join(args[1:])

        client = await self.server_manager.get_client(ctx.guild.id, ctx)
        playlist = client.get_playlist_by_name(old_name)

        if not playlist:
            no_pl_found = craft_no_playlist_found(old_name)
            await ctx.send(embed = no_pl_found)
            return
        
        playlist.name = new_name

        await client.update_playlist_changes_db()

        pl_renamed_embed = craft_playlist_renamed(old_name, new_name)
        await ctx.send(embed = pl_renamed_embed)


        



        
        