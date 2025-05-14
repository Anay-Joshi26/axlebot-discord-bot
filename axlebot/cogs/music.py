import discord
from discord.ext import commands
from core.commands_handler import rate_limit, audio_command_check, in_voice_channel, cooldown_time
from music.song_request_handler import determine_query_type
from models.song import Song, LyricsStatus
import asyncio
from music.utils.message_crafter import *
from core.server_manager import ServerManager
from models.client import Client
from music.songs_queue import SongQueue
from discord.ext.commands import BucketType, CommandOnCooldown

PAID_COOLDOWN : float = 1
NON_PAID_COOLDOWN : float = 5

class MusicPlaybackButtons(discord.ui.View):
    def __init__(self, ctx : commands.Context, client : Client):
        super().__init__(timeout=client.queue.current_song.duration+180)
        self.ctx = ctx
        self.client = client

    @discord.ui.button(style=discord.ButtonStyle.gray, label='⏯ Pause/Resume')
    async def pause_resume_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = self.client.voice_client

        if voice_client is None:
            await interaction.response.send_message("The bot is not connected to a voice channel", ephemeral = True)

        if voice_client.is_playing():
            voice_client.pause()
            self.client.queue.current_song.stop()
            await interaction.message.add_reaction('⏸️')
            # await interaction.message.clear_reaction('▶️')
            await interaction.response.defer()

        elif voice_client.is_paused():
            voice_client.resume()
            self.client.queue.current_song.play()
            #await interaction.message.add_reaction('▶️')
            await interaction.message.clear_reaction('⏸️')
            await interaction.response.defer()
        else:
            await self.ctx.send("Cannot pause/resume song, due to some complications", ephemeral = True)

    @discord.ui.button(style=discord.ButtonStyle.gray, label='⏭️ Skip')
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer()

        if self.client.voice_client is None:
            await self.ctx.send("The bot is not connected to a voice channel", ephemeral = True)

        if self.client.voice_client.is_playing() and len(self.client.queue) > 0:
            self.client.voice_client.stop()
            self.client.queue.current_song.stop()

            await interaction.message.clear_reaction('⏭️')
            # await ctx.send("Skipped the song...")
        else:
            await self.ctx.send("No song is currently playing", ephemeral = True)

    @discord.ui.button(style=discord.ButtonStyle.gray, label='🔁 Repeat')
    async def repeat_btn(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer()

        if self.client.voice_client is None:
            await self.ctx.send("The bot is not connected to a voice channel")
            return
        
        try:
            await self.client.queue.repeat()
            await self.ctx.send(f"The current playing song will repeat, run `-q` to see the updated queue")
        except ValueError as e:
            await self.ctx.send(e)
        

    @discord.ui.button(style=discord.ButtonStyle.gray, label='🔂 Loop')
    async def loop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer()

        try:
            is_looping = self.client.queue.loop()
            if is_looping:
                await interaction.message.add_reaction('🔂')
            else:
                try:
                    await interaction.message.clear_reaction('🔂')
                except discord.NotFound:
                    print("Reaction not found")

        except Exception as e:
            await interaction.response.send_message(e, ephemeral = True)


class MusicCog(commands.Cog):

    """
    This cog is responsible for handling all music related commands, such as playing songs, pausing, skipping, etc.
    Playlist commands are handled in the PlaylistCog, but rely on the MusicCog to play the songs in the playlist.
    """

    def __init__(self, bot, server_manager):
        self.bot = bot
        self.server_manager : ServerManager = server_manager
        self.YT_SONG, self.SPOT_SONG, self.YT_PLAYLIST, self.SPOT_PLAYLIST, self.STD_YT_QUERY = range(5)


    async def send_play_song_embed(self, ctx, song: Song, client, is_looping = False):
        embed = craft_now_playing(song, is_looping)
        song.play()
        progress_message = await ctx.send(embed = embed, view = MusicPlaybackButtons(ctx, client), silent = True)
        song.progress_message = progress_message
        asyncio.create_task(update_progress_bar_embed(song, embed, progress_message)) # function updates the progress bar in the embed (every set interval seconds)

    @commands.command(aliases = ['mv'])
    @commands.check(in_voice_channel)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def move(self, ctx, *args):
        """
        Moves a song from one position in the queue to another
        """
        client = await self.server_manager.get_client(ctx.guild.id)
        queue = client.queue

        if len(queue) == 0:
            await ctx.send("The queue is empty, there are no songs to move")
            return

        if len(args) != 2:
            await ctx.send("Invalid number of arguments, you need to provide the current position and the new position")
            return

        try:
            current_pos = int(args[0])
            new_pos = int(args[1])
        except ValueError:
            await ctx.send("Invalid arguments, the positions must be integers")
            return

        try:
            queue.move(current_pos, new_pos)
        except ValueError as e:
            await ctx.send(e)
            return

        embed = craft_move_song(queue[new_pos-1], new_pos)
        await ctx.send(embed=embed, silent = True)

    @commands.command(aliases = ['p'])
    @commands.check(in_voice_channel)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def play(self, ctx, *args):
        query = ' '.join(args)
        client = await self.server_manager.get_client(ctx.guild.id, ctx)

        print("Client for guild found", client)
        print("Client queue", client.queue.queue)
        print("Playing client id", id(client))

        if client.voice_client is None:
            vc = await ctx.author.voice.channel.connect()
            client.voice_client = vc

        # Schedule the play_song function as a non-blocking task
        asyncio.create_task(self.play_song(ctx, client, query))


    async def play_song(self, ctx, client: Client, query: str, position : int = None):
        """
        Plays a song (or adds to queue), given a client and query
        """
        query_type = determine_query_type(query)

        queue, voice_client = client.queue, client.voice_client

        if query_type == self.YT_SONG:
            song_task = asyncio.create_task(Song.SongFromYouTubeURL(query))
        elif query_type == self.SPOT_SONG:
            song_task = asyncio.create_task(Song.SongFromSpotifyURL(query))
        elif query_type == self.YT_PLAYLIST or query_type == self.SPOT_PLAYLIST:

            qt = "yt" if query_type == self.YT_PLAYLIST else "spot"

            embed = craft_playlist_added(qt)

            await ctx.send(embed = embed)


            if query_type == self.SPOT_PLAYLIST:
                song_generator = Song.SpotifyPlaylistSongList(query, max_concurrent_song_loadings=client.max_concurrent_song_loadings)
            else:
                song_generator = Song.YouTubePlaylistSongList(query, max_concurrent_song_loadings=client.max_concurrent_song_loadings)

            # Start the generator to populate the queue
            async for song in song_generator:
                if song:
                    queue.append(song, position)
                    print(f"Added to queue: {song.name}")
                    position += 1

                # Start playing the first song if it's not already playing
                if len(queue) == 1:
                    await self.send_play_song_embed(ctx, song, client)

                    voice_client.play(
                        await song.player,
                        after = lambda e : asyncio.ensure_future(self.play_next(ctx, client), loop = self.bot.loop)
                    )

            return        
        elif query_type == self.STD_YT_QUERY:
            song_task = asyncio.create_task(Song.CreateSong(query))

        song = await song_task

        queue.append(song, position)

        if len(queue) == 1:
            await self.send_play_song_embed(ctx, song, client)

            voice_client.play(
                await song.player,
                after = lambda e : asyncio.ensure_future(self.play_next(ctx, client), loop = self.bot.loop)
            )
        else:
            if position is None:
                await ctx.send(f"**{song.name}** has been added to the queue in position `{len(queue)}`", silent = True)
            else:
                await ctx.send(f"**{song.name}** will play next after the current song", silent = True)
        
    async def play_next(self, ctx, client : Client):
        """
        Plays the next song in the queue, or informs the user that the queue is empty
        """
        queue, voice_client = client.queue, client.voice_client

        last_progress_message = queue.current_song.progress_message

        await last_progress_message.edit(view=None)

        next_song = await queue.next()

        if next_song is None:
            # queue is empty, let them know
            embed = craft_queue_empty()
            await ctx.send(embed = embed)
            return
        
        await self.send_play_song_embed(ctx, next_song, client)
        
        voice_client.play(await next_song.player, after = lambda e : asyncio.ensure_future(self.play_next(ctx, client), loop = self.bot.loop))
        # embed = craft_now_playing(next_song)
        # progress_message = await ctx.send(embed = embed)
        # next_song.progress_message = progress_message


    @commands.command(aliases = ['ps'])
    @commands.check(in_voice_channel)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def pause(self, ctx):
        client = await self.server_manager.get_client(ctx.guild.id)
        voice_client = client.voice_client

        if voice_client is None:
            await ctx.send("The bot is not connected to a voice channel")

        if voice_client.is_playing():
            voice_client.pause()
            client.queue.current_song.stop()

            await ctx.message.add_reaction('⏸️')
            await ctx.message.clear_reaction('▶️')

            #await ctx.send("Paused the music...")
        elif voice_client.is_paused():
            await ctx.send("The music is already paused")
        else:
            await ctx.send("Cannot pause song, due to some complications")

    @commands.command(aliases = ['res'])
    @commands.check(in_voice_channel)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def resume(self, ctx):
        client = await self.server_manager.get_client(ctx.guild.id)
        voice_client = client.voice_client

        if voice_client is None:
            await ctx.send("The bot is not connected to a voice channel")

        if voice_client.is_paused():
            voice_client.resume()
            client.queue.current_song.play()

            await ctx.message.add_reaction('▶️')
            await ctx.message.clear_reaction('⏸️')

            # await ctx.send("Resumed the music...")
        elif voice_client.is_playing():
            await ctx.send("The music is already playing")
        else:
            await ctx.send("Cannot resume song, due to some complications")

    @commands.command(aliases = ['q'])
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def queue(self, ctx):
        client = await self.server_manager.get_client(ctx.guild.id)
        embed = craft_queue(client.queue)
        await ctx.send(embed = embed)

    @commands.command(aliases = ['l'])
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def lyrics(self, ctx):
        client = await self.server_manager.get_client(ctx.guild.id)
        current_song = client.queue.current_song

        if current_song is None:
            await ctx.send("No song is currently playing")
            return
        
        lyrics, status = current_song.get_lyrics()

        embed = craft_lyrics_embed(lyrics, current_song.name, current_song.artist, status)
        await ctx.send(embed = embed)

    @commands.command(aliases = ['pn', 'qn'])
    @commands.check(in_voice_channel)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def queue_next(self, ctx, *args):
        """
        In cases where a song wants to played directly after the current playing song without waiting for the other songs in the queue to finish this command can be used.

        It will insert the song directly after the first song rather than at the end of the queue.

        It can be thought of as a "play this next" or "queue this next" hence -pn or -qn.
        """
        query = ' '.join(args)
        client = await self.server_manager.get_client(ctx.guild.id)

        if client.voice_client is None:
            vc = await ctx.author.voice.channel.connect()
            client.voice_client = vc

        if len(client.queue) == 0:
            position = None
        else:
            position = 1

        # Schedule the play_song function as a non-blocking task
        asyncio.create_task(self.play_song(ctx, client, query, position = position))


        

    @commands.command(aliases = ['skp', 'sk'])
    @commands.check(in_voice_channel)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def skip(self, ctx):
        client = await self.server_manager.get_client(ctx.guild.id)
        queue, voice_client = client.queue, client.voice_client

        if voice_client is None:
            await ctx.send("The bot is not connected to a voice channel")

        if voice_client.is_playing() and len(queue) > 0:
            voice_client.stop()
            queue.current_song.stop()

            await ctx.message.add_reaction('⏭️')
            # await ctx.send("Skipped the song...")
        else:
            await ctx.send("No song is currently playing")

    @commands.command(aliases=['stp'])
    @commands.check(in_voice_channel)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def stop(self, ctx: commands.Context):
        client = await self.server_manager.get_client(ctx.guild.id)
        voice_client = client.voice_client

        if voice_client is None:
            await ctx.send("The bot is not connected to a voice channel")
            return
        
        delete_after = 10

        embed = craft_bot_music_stopped(delete_after=delete_after)
        await ctx.send(embed=embed, delete_after=delete_after)

        client.queue.current_song.stop()
        voice_client.stop()
        await voice_client.disconnect(); client.voice_client = None
        client.queue.clear()

   

    @commands.command(aliases = ['lp'])
    @commands.check(in_voice_channel)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def loop(self, ctx):
        client = await self.server_manager.get_client(ctx.guild.id)
        try:
            is_looping = client.queue.loop()
            if is_looping:
                await ctx.message.add_reaction('🔁')
            else:
                try:
                    await ctx.message.clear_reaction('🔁')
                except discord.NotFound:
                    pass
        except Exception as e:
            await ctx.send(e)
        

    @commands.command(aliases = ['del'])
    @commands.check(in_voice_channel)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def delete(self, ctx, pos : int):
        
        client = await self.server_manager.get_client(ctx.guild.id)
        queue = client.queue

        if len(queue) == 0:
            await ctx.send("The queue is empty, there are no songs to delete")
            return
        
        if pos == 1:
            await ctx.send("You cannot delete the currently playing song, use `-skip` to skip the song instead")
            return

        if pos < 2 or pos > len(queue):
            await ctx.send(f"Invalid position, the queue has `{len(queue)}` songs")
            return

        song = queue.pop(pos-1)
        embed = craft_delete_song(song)
        await ctx.send(embed=embed, silent = True)
        

    @commands.command(aliases = ['rep'])
    @commands.check(in_voice_channel)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def repeat(self, ctx, num : int = 1):
        client = await self.server_manager.get_client(ctx.guild.id)

        if client.voice_client is None:
            await ctx.send("The bot is not connected to a voice channel")
            return
        
        try:
            await client.queue.repeat(num)
            await ctx.send(f"Repeating the current song {num} times, run `-q` to see the updated queue")
        except ValueError as e:
            await ctx.send(e)

        
        





    
        

            


        

    





        

# def setup(bot):
#     bot.add_cog(MusicCog(bot, server_manager))



    
