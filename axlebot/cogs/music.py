import discord
from discord.ext import commands
from core.commands_handler import *
from music.song_request_handler import determine_query_type
from models.song import Song, LyricsStatus
import asyncio
from utils.message_crafter import *
from core.server_manager import ServerManager
from core.lavalink import LavalinkVoiceClient
from models.client import Client
from music.songs_queue import SongQueue
from discord.ext.commands import BucketType, CommandOnCooldown
from utils import parse_seek_time
from copy import deepcopy
#import lavalink
import core.extensions
import traceback
from lavalink import Timescale, Vibrato, Rotation, Karaoke, Equalizer
import shlex

PAID_COOLDOWN : float = 1
NON_PAID_COOLDOWN : float = 5

class MusicPlaybackButtons(discord.ui.View):
    def __init__(self, ctx : commands.Context, client : Client):
        super().__init__(timeout=client.queue.current_song.duration+43200)
        self.ctx = ctx
        self.client = client

    # @discord.ui.button(style=discord.ButtonStyle.gray, label='⏯ Pause/Resume')
    # @commands.check(in_voice_channel)
    # async def pause_resume_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     try:
    #         await in_voice_channel_interaction(interaction)
    #     except NotInVoiceChannelCheckFailure as e:
    #         await interaction.response.send_message(str(e), ephemeral=True)
    #         return

    #     voice_client = self.client.voice_client

    #     if voice_client is None:
    #         await interaction.response.send_message("The bot is not connected to a voice channel", ephemeral = True)

    #     if voice_client.is_playing():
    #         await voice_client.pause()
    #         self.client.queue.current_song.stop()
    #         await interaction.message.add_reaction('⏸️')
    #         # await interaction.message.clear_reaction('▶️')
    #         await interaction.response.defer()

    #     elif voice_client.is_paused():
    #         voice_client.resume()
    #         self.client.queue.current_song.play()
    #         #await interaction.message.add_reaction('▶️')
    #         await interaction.message.remove_reaction('⏸️', interaction.guild.me)
    #         await interaction.response.defer()
    #     else:
    #         await self.ctx.send("Cannot pause/resume song, due to some complications", ephemeral = True)

    @discord.ui.button(style=discord.ButtonStyle.gray, label='⏭️ Skip', row = 1)
    @commands.check(in_voice_channel)
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await in_voice_channel_interaction(interaction)
        except NotInVoiceChannelCheckFailure as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        await interaction.response.defer()

        if self.client.voice_client is None:
            await self.ctx.send("The bot is not connected to a voice channel", ephemeral = True)

        if "self.client.voice_client.is_playing() and " and len(self.client.queue) > 0:
            await self.client.voice_client.stop()
            self.client.queue.current_song.stop()

            await interaction.message.remove_reaction('⏭️', interaction.guild.me)
            # await ctx.send("Skipped the song...")
        else:
            await self.ctx.send("No song is currently playing", ephemeral = True)

    @discord.ui.button(style=discord.ButtonStyle.gray, label='🔂 Repeat', row = 1)
    @commands.check(in_voice_channel)
    async def repeat_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await in_voice_channel_interaction(interaction)
        except NotInVoiceChannelCheckFailure as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        await interaction.response.defer()

        if self.client.voice_client is None:
            await self.ctx.send("The bot is not connected to a voice channel")
            return
        
        try:
            await self.client.queue.repeat()
            await self.ctx.send(f"The current playing song will repeat, run `-q` to see the updated queue", delete_after=15)
        except ValueError as e:
            await self.ctx.send(e)
        

    @discord.ui.button(style=discord.ButtonStyle.gray, label='🔁 Loop', row = 1)
    @commands.check(in_voice_channel)
    async def loop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await in_voice_channel_interaction(interaction)
        except NotInVoiceChannelCheckFailure as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        await interaction.response.defer()

        try:
            is_looping = self.client.queue.loop()
            if is_looping:
                await interaction.message.add_reaction('🔁')
            else:
                try:
                    await interaction.message.remove_reaction('🔁', interaction.guild.me)
                except discord.NotFound:
                    print("Reaction not found")

        except Exception as e:
            await interaction.response.send_message(e, ephemeral = True)

    @discord.ui.button(style=discord.ButtonStyle.gray, label='⏪ 10s', row = 0)
    @commands.check(in_voice_channel)
    async def seek_backwards_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await in_voice_channel_interaction(interaction)
        except NotInVoiceChannelCheckFailure as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        await interaction.response.defer()
        try:
            await self.ctx.bot.get_cog('MusicCog').seek_by(self.ctx, -10)
        except Exception as e:
            await interaction.followup.send(f"Failed to seek: {e}", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.gray, label='⏯ Pause/Resume', row = 0)
    @commands.check(in_voice_channel)
    async def pause_resume_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await in_voice_channel_interaction(interaction)
        except NotInVoiceChannelCheckFailure as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        voice_client = self.client.voice_client

        if voice_client is None:
            await interaction.response.send_message("The bot is not connected to a voice channel", ephemeral = True)

        if voice_client.is_playing():
            print("Pausing song")
            await voice_client.pause()
            self.client.queue.current_song.stop()
            await interaction.message.add_reaction('⏸️')
            # await interaction.message.clear_reaction('▶️')
            await interaction.response.defer()

        elif voice_client.is_paused():
            print("Resuming song")
            await voice_client.resume()
            self.client.queue.current_song.play()
            #await interaction.message.add_reaction('▶️')
            await interaction.message.remove_reaction('⏸️', interaction.guild.me)
            await interaction.response.defer()
        else:
            await self.ctx.send("Cannot pause/resume song, due to some complications", ephemeral = True)

    @discord.ui.button(style=discord.ButtonStyle.gray, label='10s ⏩', row = 0)
    @commands.check(in_voice_channel)
    async def seek_forward_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await in_voice_channel_interaction(interaction)
        except NotInVoiceChannelCheckFailure as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        await interaction.response.defer()
        try:
            await self.ctx.bot.get_cog('MusicCog').seek_by(self.ctx, 10)
        except Exception as e:
            await interaction.followup.send(f"Failed to seek: {e}", ephemeral=True)



class MusicCog(commands.Cog):

    """
    This cog is responsible for handling all music related commands, such as playing songs, pausing, skipping, etc.
    Playlist commands are handled in the PlaylistCog, but rely on the MusicCog to play the songs in the playlist.
    """

    def __init__(self, bot, server_manager):
        self.bot = bot
        self.server_manager : ServerManager = server_manager
        self.YT_SONG, self.SPOT_SONG, self.YT_PLAYLIST, self.SPOT_PLAYLIST, self.STD_YT_QUERY = range(5)


    async def send_play_song_embed(self, ctx, song: Song, client, is_looping = False, play = True):
        client.interupt_inactivity_timer()
        embed = await craft_now_playing(song, is_looping)
        if play:
            song.play()
        progress_message = await ctx.send(embed = embed, view = MusicPlaybackButtons(ctx, client), silent = True)
        song.progress_message = progress_message
        #asyncio.create_task(update_progress_bar_embed(song, embed, progress_message)) # function updates the progress bar in the embed (every set interval seconds)
        asyncio.create_task(update_progress_bar_embed(song, embed, "progress_message")) # function updates the progress bar in the embed (every set interval seconds)

    @commands.command(aliases = ['mv'])
    @commands.check(in_voice_channel)
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.guild)
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
            await queue.move(current_pos, new_pos)
        except ValueError as e:
            await ctx.send(e)
            return

        embed = craft_move_song(queue[new_pos-1], new_pos)
        await ctx.send(embed=embed, silent = True)

    @commands.command(aliases = ['p'])
    @commands.check(in_voice_channel)
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.guild)
    async def play(self, ctx: commands.Context, *, query):
        try:
            client = await self.server_manager.get_client(ctx.guild.id, ctx)

            async with client.client_lock:
                if client.voice_client is None:
                    print("Client voice client is None, connecting to voice channel")
                    vc = await ctx.author.voice.channel.connect(cls = LavalinkVoiceClient)
                    print("Connected to voice channel", vc.channel.name)
                    client.voice_client = vc

            # Schedule the play_song function as a non-blocking task
            asyncio.create_task(self.play_song(ctx, client, query))
        except Exception as e:
            print(f"Error in play command: {e}")
            await ctx.send(embed=craft_general_error(), delete_after = 20)
            traceback.print_exc()


    async def play_song(self, ctx: commands.Context, client: Client, query: str, position : int = None):
        """
        Plays a song (or adds to queue), given a client and query
        """
        try:
            query_type = determine_query_type(query)

            queue, voice_client = client.queue, client.voice_client

            client.interupt_inactivity_timer()

            fetching_song_message = await ctx.send("*Loading music, please wait...*", silent = True)

            if query_type == self.YT_SONG:
                song_task = asyncio.create_task(Song.SongFromYouTubeURL(query))
            elif query_type == self.SPOT_SONG:
                song_task = asyncio.create_task(Song.SongFromSpotifyURL(query))
            elif query_type == self.YT_PLAYLIST or query_type == self.SPOT_PLAYLIST:

                qt = "yt" if query_type == self.YT_PLAYLIST else "spot"

                stop_event = asyncio.Event()
                client.stop_event = stop_event

                if query_type == self.SPOT_PLAYLIST:
                    song_generator = Song.SpotifyPlaylistSongList(query, max_concurrent_song_loadings=client.max_concurrent_song_loadings, stop_event=stop_event)
                else:
                    song_generator = Song.YouTubePlaylistSongList(query, max_concurrent_song_loadings=client.max_concurrent_song_loadings, stop_event=stop_event)

                # embed = craft_playlist_added(qt)
                # await ctx.send(embed = embed)

                # Start the generator to populate the queue
                position = len(queue) if position is None else position
                i = 0
                auto_play_updated = False
                async for song in song_generator:
                    if song:
                        if i == 0:
                            # if we are here, it means that no error has occured, and so the yt url is valid
                            embed = craft_playlist_added(qt)
                            await ctx.send(embed = embed)

                        await queue.append(song, position, update_auto_play=False)
                        print(f"Added to queue: {song.name}")
                        position += 1

                        if len(queue) == 5:
                            auto_play_updated = True
                            await client.queue.update_auto_play_songs()

                    # Start playing the first song if it's not already playing
                    if len(queue) == 1:
                        await fetching_song_message.delete()
                        song.is_first_in_queue = True
                        await self.send_play_song_embed(ctx, song, client)

                        player = await song.player

                        if player is None:
                            await ctx.send(embed=craft_general_error(f"YouTube has temporarily blocked `{song.name}` :(, please try again later"), delete_after = 20)
                            asyncio.create_task(self.play_next(ctx, client))
                            return

                        await voice_client.play(
                            player,
                            after = lambda e: self.bot.loop.call_soon_threadsafe(
                                        lambda: asyncio.ensure_future(self._after_playback(e, ctx, client))
                                    )

                        )

                    i += 1
                if not auto_play_updated and client.server_config.auto_play:
                    # If we have added songs to the queue, we can update the auto play songs
                    await client.queue.update_auto_play_songs()

                return        
            elif query_type == self.STD_YT_QUERY:
                song_task = asyncio.create_task(Song.CreateSong(query))
            error_occured = False
            try:
                song = await song_task
                if song is None:
                    error_occured = True
            except Exception as e:
                error_occured = True
            
            if error_occured:
                await fetching_song_message.delete()
                await ctx.send(embed = craft_general_error("The song could not be found with the provided query"), delete_after = 20)
                return

            await queue.append(song, position)

            if len(queue) == 1:
                await fetching_song_message.delete()
                song.is_first_in_queue = True
                await self.send_play_song_embed(ctx, song, client)

                player = await song.player

                if player is None:
                    await ctx.send(embed=craft_general_error(f"YouTube has temporarily blocked `{song.name}` :(, please try again later"), delete_after = 20)
                    asyncio.create_task(self.play_next(ctx, client))
                    return

                await voice_client.play(
                    player,
                    after = lambda e: self.bot.loop.call_soon_threadsafe(
                                        lambda: asyncio.ensure_future(self._after_playback(e, ctx, client))
                                    )
                )
            else:
                await fetching_song_message.delete()
                if position is None:
                    await ctx.send(f"**{song.name}** has been added to the queue in position `{len(queue)}`", silent = True)
                else:
                    await ctx.send(f"**{song.name}** will play next after the current song", silent = True)
        except Exception as e:
            await fetching_song_message.delete()
            print(f"Error in play command: {e}")
            await ctx.send(embed=craft_general_error(), delete_after = 20)
            traceback.print_exc()

        
    async def play_next(self, ctx, client : Client):
        """
        Plays the next song in the queue, or informs the user that the queue is empty
        """
        if hasattr(client, "stop_command_called") and client.stop_command_called:
            # If the stop_command was called, we do not play the next song
            client.stop_command_called = False
            return
        try:
            queue, voice_client = client.queue, client.voice_client

            last_progress_message = queue.current_song.progress_message

            await last_progress_message.edit(view=None)

            if client.server_config.delete_message_after_play:
                try:
                    await last_progress_message.delete()
                except discord.NotFound:
                    print("Progress message not found, it might have been deleted already")

            last_song = queue.current_song

            next_song: Song = await queue.next()

            if next_song is None and not client.server_config.auto_play:
                # queue is empty, let them know

                embed = craft_queue_empty()
                await ctx.send(embed = embed)
                if client.voice_client is not None:
                    await client.start_inactivity_timer(ctx) 
                return
            
            if next_song is None and client.server_config.auto_play:
                # The queue is empty, but auto play is enabled, so we will play a song from the recommendations
                # if client.voice_client is None:
                #     return
                recommendations = await Song.get_song_recommendations([last_song], limit = 5)
                if not recommendations:
                    await ctx.send(embed=craft_general_error("No recommendations found :("), delete_after = 20)
                    embed = craft_queue_empty()
                    await ctx.send(embed = embed)
                    if client.voice_client is not None:
                        await client.start_inactivity_timer(ctx) 
                    return
                
                next_song = recommendations[0]
                for s in recommendations:
                    await client.queue.append(s)
            
            await self.send_play_song_embed(ctx, next_song, client)

            player = await next_song.player

            if player is None:
                await ctx.send(embed=craft_general_error(f"YouTube has temporarily blocked `{next_song.name}` :(, please try again later"), delete_after = 20)
                asyncio.create_task(self.play_next(ctx, client))
                return
            
            await voice_client.play(player, after = lambda e: self.bot.loop.call_soon_threadsafe(
                                        lambda: asyncio.ensure_future(self._after_playback(e, ctx, client))
                                    ))
            # embed = craft_now_playing(next_song)
            # progress_message = await ctx.send(embed = embed)
            # next_song.progress_message = progress_message
        except Exception as e:
            print(f"Error in play_next: {e}")
            await ctx.send(embed=craft_general_error(), delete_after = 20)
            traceback.print_exc()

    async def _after_playback(self, error, ctx, client):
        if error:
            print(f"Error in play_next: {error}")
            await ctx.send(embed=craft_general_error(), delete_after = 20)

        await self.play_next(ctx, client)

    @commands.command(aliases = ['ps'])
    @commands.check(in_voice_channel)
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.guild)
    async def pause(self, ctx):
        client = await self.server_manager.get_client(ctx.guild.id)
        voice_client = client.voice_client

        if voice_client is None:
            await ctx.send("The bot is not connected to a voice channel")

        if voice_client.is_playing():
            await voice_client.pause()
            client.queue.current_song.stop()

            await ctx.message.add_reaction('⏸️')
            await ctx.message.remove_reaction('▶️', ctx.me)#clear_reaction('▶️')

            #await ctx.send("Paused the music...")
        elif voice_client.is_paused():
            await ctx.send("The music is already paused")
        else:
            await ctx.send("Cannot pause song, due to some complications")

    @commands.command(aliases = ['res'])
    @commands.check(in_voice_channel)
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.guild)
    async def resume(self, ctx):
        client = await self.server_manager.get_client(ctx.guild.id)
        voice_client = client.voice_client

        if voice_client is None:
            await ctx.send("The bot is not connected to a voice channel")

        if voice_client.is_paused():
            await voice_client.resume()
            client.queue.current_song.play()

            await ctx.message.add_reaction('▶️')
            await ctx.message.remove_reaction('⏸️', ctx.me)

            # await ctx.send("Resumed the music...")
        elif voice_client.is_playing():
            await ctx.send("Music is already playing")
        else:
            await ctx.send("Cannot resume song, due to some complications")

    @commands.command(aliases = ['q'])
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.guild)
    async def queue(self, ctx: commands.Context, num : int | None = None, *args):
        client = await self.server_manager.get_client(ctx.guild.id)
        print("num", num)
        if num is None or num > len(client.queue) or num < 1:
            num = None
            #print("No number provided or number is invalid, showing full queue")
        is_live = args and args[-1] in ['-l', '-live', '-livequeue', 'l', 'live', 'livequeue']
        embed = craft_queue(client, num = num, live = is_live)
        try:
            if is_live:
                if hasattr(client, 'live_queue_message'):
                    try:
                        await client.live_queue_message.delete()
                    except discord.NotFound:
                        delattr(client, 'live_queue_message')
                live_queue_message = await ctx.send(embed = embed)
                client.live_queue_message = live_queue_message
            else:
                await ctx.send(embed = embed)
        except Exception as e:
            await ctx.send(embed = discord.Embed(
                title="Too many songs in queue",
                description="The queue is too long to send through Discord. But don't worry, the songs are still queued up!",
                colour=embed.colour,
            ))

    @commands.command(aliases = ['l'])
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.guild)
    async def lyrics(self, ctx):
        client = await self.server_manager.get_client(ctx.guild.id)
        current_song: Song = client.queue.current_song

        if current_song is None:
            await ctx.send("No song is currently playing")
            return
        
        lyrics, status = current_song.get_lyrics()

        embed = craft_lyrics_embed(lyrics, current_song.name, current_song.artist, status)
        await ctx.send(embed = embed)

    @commands.command(aliases = ['pn', 'qn'])
    @commands.check(in_voice_channel)
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.guild)
    async def queue_next(self, ctx, *args):
        """
        In cases where a song wants to played directly after the current playing song without waiting for the other songs in the queue to finish this command can be used.

        It will insert the song directly after the first song rather than at the end of the queue.

        It can be thought of as a "play this next" or "queue this next" hence -pn or -qn.
        """
        query = ' '.join(args)
        client = await self.server_manager.get_client(ctx.guild.id)

        if client.voice_client is None:
            vc = await ctx.author.voice.channel.connect(cls = LavalinkVoiceClient)
            client.voice_client = vc

        position = None if len(client.queue) == 0 else 1

        # Schedule the play_song function as a non-blocking task
        asyncio.create_task(self.play_song(ctx, client, query, position = position))


        

    @commands.command(aliases = ['skp', 'sk'])
    @commands.check(in_voice_channel)
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.guild)
    async def skip(self, ctx):
        client = await self.server_manager.get_client(ctx.guild.id)
        queue, voice_client = client.queue, client.voice_client

        if voice_client is None:
            await ctx.send("The bot is not connected to a voice channel")

        if "voice_client.is_playing()" and len(queue) > 0:
            await voice_client.stop()
            queue.current_song.stop()

            await ctx.message.add_reaction('⏭️')
            # await ctx.send("Skipped the song...")
        else:
            await ctx.send("No song is currently playing")

    @commands.command(aliases=['stp'])
    @commands.check(in_voice_channel)
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.guild)
    async def stop(self, ctx: commands.Context):
        client = await self.server_manager.get_client(ctx.guild.id)
        voice_client = client.voice_client
        client.stop_command_called = True

        if voice_client is None:
            await ctx.send("The bot is not connected to a voice channel")
            return
        
        await client.stop(ctx)
        # delete_after = 10

        # embed = craft_bot_music_stopped(delete_after=delete_after)
        # await ctx.send(embed=embed, delete_after=delete_after)

        # client.queue.current_song.stop()
        # await voice_client.stop()
        # await voice_client.disconnect(); client.voice_client = None
        # client.queue.clear()

    # async def stop(self, ctx: commands.Context, client: Client, delete_after: int = 10):
    #     """
    #     Stops the music playback and clears the queue.
    #     """
    #     embed = craft_bot_music_stopped(delete_after=delete_after)
    #     await ctx.send(embed=embed, delete_after=delete_after)

    #     client.queue.current_song.stop()
    #     client.await voice_client.stop()
    #     await client.voice_client.disconnect(); client.voice_client = None
    #     client.queue.clear()

    @commands.command(aliases = ['lp'])
    @commands.check(in_voice_channel)
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.guild)
    async def loop(self, ctx):
        client = await self.server_manager.get_client(ctx.guild.id)
        try:
            is_looping = client.queue.loop()
            if is_looping:
                await ctx.message.add_reaction('🔁')
            else:
                try:
                    await ctx.message.remove_reaction('🔁', ctx.me)
                except discord.NotFound:
                    pass
        except Exception as e:
            await ctx.send(e)
        

    @commands.command(aliases = ['del'])
    @commands.check(in_voice_channel)
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.guild)
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

        song = await queue.pop(pos-1)
        embed = craft_delete_song(song)
        await ctx.send(embed=embed, silent = True)
    
    @commands.command(aliases = ['shuf', 'sh', 'shuff'])
    @commands.check(in_voice_channel)
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.guild)
    async def shuffle(self, ctx):
        client = await self.server_manager.get_client(ctx.guild.id)

        if client.voice_client is None:
            await ctx.send("The bot is not connected to a voice channel")
            return
        
        try:
            await client.queue.shuffle()
            await ctx.send(f"The queue has been shuffled, run `-q` to see the updated queue", delete_after=15)
        except ValueError as e:
            await ctx.send(e)

    @commands.command(aliases = ['rep'])
    @commands.check(in_voice_channel)
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.guild)
    async def repeat(self, ctx, num : int = 1, *args):
        client = await self.server_manager.get_client(ctx.guild.id)

        if client.voice_client is None:
            await ctx.send("The bot is not connected to a voice channel")
            return
        
        # try:
        #     num = int(num)
        #     print(f"Repeating the current song {num} times")
        # except ValueError as e:
        #     await ctx.send("Please provide a valid number (between 1 and 20)")
        #     return
        rep_queue = args and (args[-1] in ['-q', '-queue', 'q', 'queue'])
        print(f"rep_queue: {rep_queue}")
        
        if num < 1:
            await ctx.send("A song cannot be repeated less than 1 time, please provide a valid number (1-20)")
            return
        if num > 20:
            await ctx.send("A limit of 20 repetitions has been set, please provide a valid number (1-20)")
            return
        
        try:
            if rep_queue:
                queue_to_repeat = [await song.copy() for song in client.queue]
                for _ in range(num):  # Repeat the current queue num times
                    for song in queue_to_repeat:
                        await client.queue.append(song, update_auto_play=False)
                await ctx.send(f"Repeating the **entire queue {num}** times. Run `-q` to see the updated queue.")

            else:
                await client.queue.repeat(num)
                await ctx.send(f"Repeating **the current song {num}** times, run `-q` to see the updated queue")
        except ValueError as e:
            await ctx.send(e)

    @commands.command(aliases = ['nowplaying', 'nwp', 'nowpl', 'nwpl'])
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.guild)
    async def now_playing(self, ctx):
        client = await self.server_manager.get_client(ctx.guild.id)

        if client.voice_client is None or client.queue.current_song is None:
            await ctx.send("No song is currently playing, `-p <song name>` to play a song")
            return
        
        current_song: Song = client.queue.current_song
        if current_song.progress_message is not None:
            await current_song.progress_message.delete()
            current_song.progress_message = None # to avoud errors for proress message being invalid

        embed = await craft_now_playing(current_song)
        progress_message = await ctx.send(embed = embed, view = MusicPlaybackButtons(ctx, client), silent = True)
        current_song.progress_message = progress_message

    @commands.command()
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.guild)
    async def seek(self, ctx, new_time: str):
        client = await self.server_manager.get_client(ctx.guild.id)

        if client.voice_client is None or client.queue.current_song is None:
            await ctx.send("No song is currently playing, `-p <song name>` to play a song")
            return
        
        info_msg = """
                You can use any of the following time formats when seeking:

                • `SECONDS` → `75` (e.g. 1 minute 15 seconds)  
                • `MM:SS` → `01:15`  
                • `HH:MM:SS` → `00:01:15`  
                • `SECONDS.FRACTION` → `75.5`
                """

        current_song: Song = client.queue.current_song

        try:
            mseconds_into_song = int(parse_seek_time(new_time) * 1000)
        except ValueError as e:
            await ctx.send(embed=craft_general_error(f"Invalid time format: `{new_time}`. Please use one of the formats mentioned below.\n{info_msg}"), delete_after = 90)
            return
        
        try:
            await client.voice_client.player.seek(mseconds_into_song)
            await ctx.message.add_reaction('✅') 
        except Exception as e:
            await ctx.send(embed=craft_general_error(f"Failed to seek to `{new_time}`. Please ensure the format is correct.\n{info_msg}"), delete_after = 90)
            return

        # new_player = await current_song.get_fresh_player(additional_before_options= f"-ss {new_time}")
        # if new_player is None:
        #     await ctx.send(embed=craft_general_error(f"Failed to seek to `{new_time}`. Please ensure the format is correct.\n{info_msg}"))
        #     return
        
        # was_paused = client.voice_client.is_paused()
        # client.vc_stopped_due_to_seek = True  # Set this flag to indicate that the voice client was stopped due to seeking
        # await client.voice_client.stop()
        # current_song.stop()
        # await client.voice_client.play(
        #     new_player,
        #     after=lambda e: self.bot.loop.call_soon_threadsafe(
        #         lambda: asyncio.ensure_future(self._after_playback(e, ctx, client))
        #     )
        # )
        # if was_paused:
        #     await client.voice_client.pause()
        #     current_song.stop()
        # else:
        #     current_song.play()
        current_song.seconds_played = mseconds_into_song // 1000
        # #current_song.player = new_player 
        



    async def seek_by(self, ctx, seconds: int):
        client = await self.server_manager.get_client(ctx.guild.id)
        if client.voice_client is None or client.queue.current_song is None:
            await ctx.send("No song is currently playing, `-p <song name>` to play a song")
            return False
        
        if seconds == 0:
            await ctx.send("You must provide a non-zero number of seconds to seek.")
            return False

        new_position = (client.queue.current_song.seconds_played + seconds) * 1000 # Convert seconds to milliseconds
        if new_position < 0:
            new_position = 0  # Clamp to start of song

        info_msg = """
            You can use any of the following time formats when seeking:

            • `SECONDS` → `75` (e.g. 1 minute 15 seconds)  
            • `MM:SS` → `01:15`  
            • `HH:MM:SS` → `00:01:15`  
            • `SECONDS.FRACTION` → `75.5`
            """

        current_song: Song = client.queue.current_song
        try:
            await client.voice_client.player.seek(new_position)
            await ctx.message.add_reaction('✅') 
        except Exception as e:
            await ctx.send(embed=craft_general_error(f"Failed to seek to `{new_position}`. Please ensure the format is correct.\n{info_msg}"), delete_after = 90)
            return
        # new_player = await current_song.get_fresh_player(additional_before_options=f"-ss {new_position}")

        # if new_player is None:
        #     await ctx.send(embed=craft_general_error(f"Failed to seek to `{new_position}` seconds. Please ensure the format is correct.\n{info_msg}"))
        #     return False

        # was_paused = client.voice_client.is_paused()
        # client.vc_stopped_due_to_seek = True
        # await client.voice_client.stop()
        # current_song.stop()
        # await client.voice_client.play(
        #     new_player,
        #     after=lambda e: self.bot.loop.call_soon_threadsafe(
        #         lambda: asyncio.ensure_future(self._after_playback(e, ctx, client))
        #     )
        # )
        # if was_paused:
        #     await client.voice_client.pause()
        # else:
        #     current_song.play()
        
        current_song.seconds_played = new_position // 1000
        #current_song.player = new_player
        # return True


    @commands.command(aliases=['fwd', 'fw'])
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type=BucketType.guild)
    async def forward(self, ctx, seconds: int):
        if seconds < 0:
            await ctx.send("Cannot forward a song by a negative amount of seconds, please provide a positive number")
            return
        await self.seek_by(ctx, seconds)


    @commands.command(aliases=['rw', 'rew'])
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type=BucketType.guild)
    async def rewind(self, ctx, seconds: int):
        if seconds < 0:
            await ctx.send("Cannot rewind a song by a negative amount of seconds, please provide a positive number")
            return
        await self.seek_by(ctx, -seconds)

    @commands.command(
        aliases=['sf', 'apply_filters', 'applyfilters', 'set_filter', 'setfilter', 'apply_filter']
    )
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type=BucketType.guild)
    async def set_filters(self, ctx, *filters):
        client = await self.server_manager.get_client(ctx.guild.id)
        player = getattr(client.voice_client, 'player', None)

        ALLOWED_FILTERS = {
            "timescale_speed",
            "timescale_pitch",
            "timescale_rate",
            "vibrato_depth",
            "vibrato_frequency",
            "bassboost",
            "rotation",
            "karaoke_level"
        }


        if not player or not player.is_playing:
            return await ctx.send("No song is currently playing. Use `-p <song name>` to play something.")

        adding = await ctx.send("Setting filters, please wait...")

        try:
            tokens = shlex.split(" ".join(filters))
        except ValueError:
            await adding.delete()
            return await ctx.send("Invalid filter format. Use quotes if needed.")

        parsed = {}
        current_key = None
        for token in tokens:
            if token.startswith('-'):
                current_key = token.lstrip('-')
            elif current_key:
                print(f"Processing token: {token}, current_key: {current_key}")
                if current_key not in ALLOWED_FILTERS:
                    await adding.delete()
                    return await ctx.send(f"Invalid filter name: `{current_key}`. Allowed filters: {', '.join(ALLOWED_FILTERS)}", delete_after=40)
                try:
                    parsed[current_key] = float(token)
                    current_key = None
                except ValueError:
                    await adding.delete()
                    return await ctx.send(f"Invalid value for `-{current_key}` `{token}`", delete_after=30)
        
        if not parsed:
            await adding.delete()
            return await ctx.send("No valid filters provided. Use `-sf -<filter_name> <value>` format.", delete_after=30)

        # Prepare filter objects
        filters_to_apply = []

        # Timescale
        timescale_kwargs = {}
        for k in ['timescale_speed', 'timescale_pitch', 'timescale_rate']:
            if k in parsed:
                timescale_kwargs[k.split('_')[1]] = parsed[k]
        if timescale_kwargs:
            filters_to_apply.append(Timescale(**timescale_kwargs))

        # Vibrato
        vibrato_kwargs = {}
        for k in ['vibrato_depth', 'vibrato_frequency']:
            if k in parsed:
                vibrato_kwargs[k.split('_')[1]] = parsed[k]
        if vibrato_kwargs:
            filters_to_apply.append(Vibrato(**vibrato_kwargs))

        # Rotation
        if 'rotation' in parsed:
            filters_to_apply.append(Rotation(rotation_hz=parsed['rotation']))

        # Karaoke
        if 'karaoke_level' in parsed:
            filters_to_apply.append(Karaoke(level=parsed['karaoke_level']))

        # Baseboost (Equalizer)
        if 'bassboost' in parsed:
            val = max(min(parsed['bassboost'], 1.0), 0.0)
            eq = Equalizer()
            eq.update(bands=[
                (0, val),                  # 25 Hz
                (1, val / 1.46),            # 40 Hz
                (2, val / 2),              # 63 Hz
                (3, val / 3),              # 100 Hz
                (4, val / 4.1),              # 160 Hz (optional)
            ])
            filters_to_apply.append(eq)

        # Apply filters, replacing previous ones
        try:
            await player.clear_filters() 
            await player.set_filters(*filters_to_apply)
            await asyncio.sleep(5.5)
            await adding.delete()
            if "timescale_speed" in parsed or "timescale_rate" in parsed:
                client.queue.current_song.increment_seconds_time_delay /= parsed.get('timescale_speed', 1.0) * parsed.get('timescale_rate', 1.0)
            #await ctx.send("✅ Filters applied successfully.")
            await ctx.message.add_reaction('✅') 
        except Exception as e:
            await adding.delete()
            await ctx.send(f"❌ Failed to apply filters: `{e}`", delete_after = 15)

    
    @commands.command(
        aliases=['remove_filters', 'reset_filters', 'resetfilters', 'removefilter', 'clearfilter', 'rmf', 'cf', 'rf'] 
    )
    @commands.check(bot_use_permissions)
    @commands.dynamic_cooldown(cooldown_time, type=BucketType.guild)
    async def clear_filters(self, ctx):
        """
        Clears all audio filters for the current song.
        """
        client = await self.server_manager.get_client(ctx.guild.id)
        player = getattr(client.voice_client, 'player', None)

        if not player or not player.is_playing:
            return await ctx.send("No song is currently playing. Use `-p <song name>` to play something.")
        
        clearing = await ctx.send("Clearing filters, please wait...")

        await player.clear_filters()
        await asyncio.sleep(5.5)
        await clearing.delete()
        client.queue.current_song.increment_seconds_time_delay = 1
        #await ctx.send("✅ All filters have been cleared.")
        await ctx.message.add_reaction('✅') 
        #player.set_equalizer()
        
        
        





    
        

            


        

    





        

# def setup(bot):
#     bot.add_cog(MusicCog(bot, server_manager))



    
