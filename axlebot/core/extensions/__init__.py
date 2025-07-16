from core.caching.managed_cache import CacheManager
from core.caching.caches import RedisCache, InMemoryCache, FirestoreCache
from core.extensions.firebase import fbc
from datetime import timedelta
import lavalink
import discord
from discord.ext import commands


intents = discord.Intents.default()

intents.voice_states = True
intents.message_content = True
intents.messages = True
intents.guilds = True

bot: commands.Bot = commands.Bot(command_prefix='-', intents=intents, help_command = None)
# bot.run(os.getenv("SECRET_KEY"))
# create the caches, with priorities (order doesnt matter here, but for readability it is sorted by priority)
# higher the priority means it will be checked first
# the value of priority doesnt matter as long as it is ordered correctly
caches = [
    InMemoryCache(priority=10, ttl=timedelta(hours=3)),  # InMemoryCache is the fastest, so it has the highest priority
    #RedisCache(priority=1, ttl=timedelta(days=7)),
    FirestoreCache(firestore_client=fbc, priority=1, ttl=None, is_db=True) # Firestore is a database, so it will not be deleted from
]

lavalink_client: lavalink.Client = None

NUM_CACHES = len(caches)

check_freq_time = timedelta(hours=1).seconds

cache_manager = CacheManager(caches=caches, check_freq_time=check_freq_time)