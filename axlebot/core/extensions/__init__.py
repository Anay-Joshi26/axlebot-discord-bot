from core.caching.managed_cache import CacheManager
from core.caching.caches import RedisCache, InMemoryCache, FirestoreCache
from core.extensions.firebase import fbc
from datetime import timedelta


NUM_CACHES = 3

# create the caches, with priorities (order doesnt matter here, but for readability it is sorted by priority)
caches = [
    InMemoryCache(priority=0, ttl=timedelta(hours=2)),
    #RedisCache(priority=1, ttl=timedelta(days=7)),
    FirestoreCache(firestore_client=fbc, priority=2, ttl=None, is_db=True) # Firestore is a database, so it will not be deleted from
]

cache_manager = CacheManager(caches=caches)