import discord
from discord.ext import commands
from core.commands_handler import rate_limit, audio_command_check, in_voice_channel, cooldown_time
from music.song_request_handler import determine_query_type, convert_to_standard_youtube_url
from models.song import Song, LyricsStatus
import asyncio
from music.utils.message_crafter import *
from core.server_manager import ServerManager
from models.client import Client
from music.songs_queue import SongQueue
from models.playlist import Playlist
from cogs.music import MusicCog
from discord.ext.commands import BucketType

class CreatePlaylistModal(discord.ui.Modal, title='Create a Playlist'):

    def __init__(self, name, ctx: commands.Context):
        super().__init__(timeout = 300)
        self.playlist_name: str = name
        self.ctx = ctx
        self.name_input = discord.ui.TextInput(label='Playlist Name', style=discord.TextStyle.short, default=f"{self.playlist_name}", required=True)
        self.song_links_input = discord.ui.TextInput(label='Songs', required=False, style=discord.TextStyle.paragraph, placeholder="https://www.youtube.com/watch?v=video_id\nhttps://open.spotify.com/track/track_id\n...")

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
    def __init__(self, name, ctx):
        super().__init__()
        self.name = name
        self.ctx = ctx

    @discord.ui.button(style=discord.ButtonStyle.success, label='Add Songs')
    async def add_songs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreatePlaylistModal(self.name, self.ctx))



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
        Adds songs to the playlist from the given list of urls.
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
            await ctx.send(embed = pl_not_found)
            return
        
        added_songs = []
        error_songs = []

        errors = False

        adding_songs_msg = await ctx.send("Adding songs...", silent = True)

        for url in urls:
            type_of_query = determine_query_type(url)

            if type_of_query == self.YT_SONG:
                url = convert_to_standard_youtube_url(url)
                song = await Song.SongFromYouTubeURL(url)
            elif type_of_query == self.SPOT_SONG:
                song = await Song.SongFromSpotifyURL(url)
            else:
                error_songs.append(url)
                errors = True
                continue

            if song is None:
                error_songs.append(url)
                errors = True
                continue

            try: 
                playlist.add_song(song)
                added_songs.append(song)
            except ValueError as e:
                songs_added_embed = craft_songs_added_to_playlist(playlist.name, added_songs)
                await ctx.send(embed=songs_added_embed)
                await ctx.send(str(e) + "\n" + "No more songs will be added to the playlist")
                return
            
        if len(added_songs) > 0:
            songs_added_embed = craft_songs_added_to_playlist(playlist.name, added_songs)
            await ctx.send(embed=songs_added_embed)

            await client.update_playlist_changes_db()

        await adding_songs_msg.delete()

        if errors:
            error_urls_embed = craft_songs_not_added(error_songs)
            await ctx.send(embed=error_urls_embed)

    @commands.command(aliases = ['as', 'addsongs'])
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def add_songs(self, ctx: commands.Context, *args):

        client = await self.server_manager.get_client(ctx.guild.id, ctx)

        if args:
            if args[0].startswith("http"):
                playlist_name = None
                urls = args
            else:
                playlist_name = ""
                i = 0

                while i < len(args) and not args[i].startswith("http"):
                    playlist_name += args[i] + " "
                    i += 1

                playlist_name = playlist_name.strip()
                urls = args[i:]
                if not urls:
                    await ctx.send("You didn't provide any songs to add", silent = True)
                    return
                
        else:
            await ctx.send("You didn't provide any songs to add", silent = True)

        try:
            if playlist_name:
                await self.add_songs_to_playlist(playlist_name, urls, ctx, client = client) 
            else:
                print("Adding songs to last added playlist", client.last_added_playlist)
                await self.add_songs_to_playlist(None, urls, ctx, client = client, playlist = client.last_added_playlist)
        except ValueError as e:
            await ctx.send(str(e))

    @commands.command(aliases = ['addsong'])
    @commands.check(in_voice_channel)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def add_song(self, ctx: commands.Context, *args) -> None:
        """
        Adds the current playing to a playlist with the given name.
        """
        if not args:
            await ctx.send("You didn't provide a playlist name")
            return

        client = await self.server_manager.get_client(ctx.guild.id, ctx)
        queue, voice_client = client.queue, client.voice_client

        if len(queue) == 0 or voice_client is None:
            await ctx.send("No song is currently playing", silent = True)
            return
        
        playlist_name = " ".join(args)
        playlist = client.get_playlist_by_name(playlist_name)

        if not playlist:
            no_pl_found = craft_no_playlist_found(playlist_name)
            await ctx.send(embed = no_pl_found)
            return
        
        current_song = queue.current_song

        try:
            playlist.add_song(current_song)
        except ValueError as e:
            await ctx.send(str(e))

        await client.update_playlist_changes_db()

        song_added_embed = craft_songs_added_to_playlist(playlist.name, [current_song])
        await ctx.send(embed = song_added_embed)
    
    @commands.command(aliases = ['qp', 'queuepl', 'queueplaylist', 'qpl', 'pp', 'playplaylist', 'playpl'])
    @commands.check(in_voice_channel)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def queue_playlist(self, ctx: commands.Context, *args):
        """
        Queues the playlist with the given name.
        """
        name = " ".join(args)
        client = await self.server_manager.get_client(ctx.guild.id, ctx)
        playlist = client.get_playlist_by_name(name)

        if not playlist:
            no_pl_found = craft_no_playlist_found(name)
            await ctx.send(no_pl_found)

        if client.voice_client is None:
            vc = await ctx.author.voice.channel.connect()
            client.voice_client = vc

        queue = client.queue

        pl_added = craft_custom_playlist_queued(name, playlist)

        await ctx.send(embed = pl_added)

        for song in playlist.songs:
            queue.append(song)

            if len(queue) == 1:
                client.voice_client.play(
                    await song.player,
                    after = lambda e : asyncio.ensure_future(self.music_cog.play_next(ctx, client), loop = self.bot.loop)
                )

                await self.music_cog.send_play_song_embed(ctx, song, client)

    @commands.command(aliases = ['pls', 'playlist_info', 'playlistinfo'])
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def playlists(self, ctx: commands.Context, *args):
        """
        Lists all the playlists created by the user
        """
        client = await self.server_manager.get_client(ctx.guild.id, ctx)

        if len(client.playlists) == 0:
            await ctx.send("You haven't created any playlists yet")
            return
        
        if args:
            playlist_name = " ".join(args)
            playlist = client.get_playlist_by_name(playlist_name)

            if not playlist:
                no_pl_found = craft_no_playlist_found(playlist_name)
                await ctx.send(embed = no_pl_found)
                return
            
            playlist_embed = craft_songs_in_playlist(playlist_name, playlist.songs)
            await ctx.send(embed = playlist_embed)

        else:
            all_playlists_embed = craft_view_all_playlists(client.playlists)
            await ctx.send(embed = all_playlists_embed)

    
    @commands.command(aliases = ['dp', 'deletepl', 'deleteplaylist'])
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


        
    @commands.command(aliases = ['remove_song', 'removesong', 'rs'])
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def delete_song_from_playlist(self, ctx: commands.Context, *args):
        pass
        # """
        # Deletes the song at the given index from the playlist with the given name
        # """
        # if not args:
        #     await ctx.send("You didn't provide a playlist name and song index")
        #     return
        
        # name = " ".join(args[:-1])
        # index = args[-1]

        # client = await self.server_manager.get_client(ctx.guild.id, ctx)
        # playlist = client.get_playlist_by_name(name)

        # if not playlist:
        #     no_pl_found = craft_no_playlist_found(name)
        #     await ctx.send(embed = no_pl_found)
        #     return
        
        # try:
        #     index = int(index)
        # except ValueError:
        #     await ctx.send("Invalid index")
        #     return

        # if index < 0 or index >= len(playlist.songs):
        #     await ctx.send("Invalid index")
        #     return
        
        # song = playlist.remove_song(index)

        # await client.update_playlist_changes_db()

        # song_deleted = craft_song_deleted_from_playlist(name, song)
        # await ctx.send(embed = song_deleted)
        



        
        