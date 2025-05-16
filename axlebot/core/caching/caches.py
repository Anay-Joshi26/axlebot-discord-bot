from core.caching.base_cache import BaseCache  
import redis.asyncio as redis
import json 
from datetime import datetime, timedelta
import asyncio

class RedisCache(BaseCache):
    """
    A Redis-based cache implementation.
    """
    
    def __init__(self, priority: int, host: str = '127.0.0.1', port: int = 6379, db: int = 0, ttl = timedelta(days=1), is_db = False):
        """
        Initializes the Redis cache.
        :param redis_client: The Redis client instance.
        :param priority: The priority of the cache.
        """
        super().__init__(priority, ttl, is_db)
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)


    async def get(self, key: str):
        """
        Retrieves an item from the Redis cache.
        :param key: The key of the item to retrieve.
        :return: The cached item or None if not found.
        """
        print(f"RedisCache.get({key})")
        value = await self.redis.get(key)
        print(f"RedisCache.get({key}) = {value}")
        if value is not None:
            return json.loads(value)
        return None
    
    async def set(self, key: str, value, ttl: timedelta = None):
        """
        Stores an item in the Redis cache.
        :param key: The key to store the item under.
        :param value: The item to store.
        :param ttl: The time to live for the item (optional).
        """
        if ttl is None:
            ttl = self.ttl

        await self.redis.set(key, json.dumps(value), ex=self.ttl.total_seconds())

    async def delete(self, key: str):
        """
        Deletes an item from the Redis cache.
        :param key: The key of the item to delete.
        """
        await self.redis.delete(key)

    async def all(self):
        pass


class InMemoryCache(BaseCache):
    """
    An in-memory cache implementation, which will likely hold actual Client objects.
    """
    
    def __init__(self, priority: int, ttl: timedelta = None, is_db = False):
        """
        Initializes the in-memory cache.

        :param priority: The priority of the cache.
        :param ttl: The time to live for cache items (optional).
        """
        super().__init__(priority, ttl, is_db)
        self.cache = {}
        #self.evict_expired_task = asyncio.create_task(self.evict_expired(self.check_freq_time))

    def sync_get(self, key: str):
        """
        Retrieves an item from the in-memory cache.

        :param key: The key of the item to retrieve.
        :return: The cached item or None if not found.
        """
        value = self.cache.get(key)
        if value is not None:
            return value
        return None

    async def get(self, key: str):
        """
        Retrieves an item from the dictionary cache.

        :param key: The key of the item to retrieve.
        :return: The cached item or None if not found.
        """
        value = self.cache.get(key)
        if value is not None:
            return value#json.loads(value)
        return None
    
    def set(self, key: str, value, ttl: timedelta = None):
        """
        Stores an item in the dictionary cache.

        :param key: The key to store the item under.
        :param value: The item to store.
        :param ttl: The time to live for the item (optional) as a timedelta
        """
        print("huh")
        expiry = datetime.now() + self.ttl if ttl is None else ttl
        self.cache[key] = (value, expiry)

    async def all(self):
        return self.cache.items()

    async def delete(self, key: str):
        """
        Deletes an item from the Redis cache.
        :param key: The key of the item to delete.
        """
        try:
            del self.cache[key]
        except KeyError:
            return None
        return None
    
    async def evict_expired(self):
        now = datetime.now()
        entries_to_delete = [(k,v) for k, (v, exp) in self.cache.items() if exp and now > exp]
        for k,_ in entries_to_delete:
            del self.cache[k]

        return entries_to_delete
    
from core.firebase import FirebaseClient
    
class FirestoreCache(BaseCache):
    """
    A Firestore-based cache implementation.
    """
    
    def __init__(self, firestore_client: FirebaseClient, priority: int, ttl: timedelta = None, is_db = True):
        """
        Initializes the Firestore cache.
        :param db: The Firestore database instance.
        :param priority: The priority of the cache.
        """
        super().__init__(priority, ttl, is_db)
        self.fbc = firestore_client
        self.evict_expired_task = asyncio.create_task(self._evict_expired(self.check_freq_time))

    async def get(self, key: str):
        """
        Retrieves an item from the Firestore cache.
        :param key: The key of the item to retrieve.
        :return: The cached item or None if not found.
        """
        value = await self.fbc.get_client_dict(key)
        if value is not None:
            return value
        return None
    
    async def set(self, key: str, value, ttl: timedelta = None):
        """
        Stores an item in the Firestore cache.
        :param key: The key to store the item under.
        :param value: The item to store.
        :param ttl: The time to live for the item (optional).
        """
        await self.fbc.set_data_for_client(key, value)

    async def all(self):
        pass

    async def delete(self, key: str):
        return
    
    async def evict_expired(self, check_every: timedelta):
        pass

        