from typing import List
from core.caching.base_cache import BaseCache
from core.caching.caches import InMemoryCache, RedisCache, FirestoreCache
from datetime import datetime, timedelta
import asyncio
import inspect
# from models.client import Client

class CacheManager:
    """
    A class to manage a caches.
    The CacheManager is in charge of promoting Client objects to higher priority caches and demoting inactive clients to lower priority caches.
    The priority is a measure of the access speed
    """
    def __init__(self, caches: List[BaseCache], check_freq_time):
        print(caches)
        self.caches = sorted(caches, key=lambda c: c.priority, reverse=True)
        self.cache_to_index = {repr(cache): i for i, cache in enumerate(self.caches)}
        self._eviction_task = None
        self.check_freq_time = check_freq_time  # Time in seconds to check for expired entries
        self.dbs = [cache for cache in self.caches if cache.is_db]

    def start(self):
        self._start_eviction_loop(self.check_freq_time)

    @property
    def active_cache(self) -> BaseCache:
        """
        Returns the active cache (the one with the highest priority).
        """
        return self.caches[0]

    async def get(self, key, return_newly_created = False):
        """
        Get an item from the cache.
        """
        key = str(key)
        for i, cache in enumerate(self.caches):
            #print(cache)
            if isinstance(cache, InMemoryCache):
                #print("InMemoryCache...........")
                try:
                    value = await self._get(key, cache)
                    #print("ID value", id(value))
                except Exception as e:
                    print(f"Exception in sync_get: {e}")
                    raise
                print(value)
            else:
                value = await self._get(key, cache)
            #print(f"Cache {i}: {cache}\nKey: {key}\nValue: {value}")
            if value is None:
                #print('aaa')
                continue

            final_client_obj, newly_created = await self._promote(key, cache, i, value, to_top=True)

            if return_newly_created:
                return final_client_obj, newly_created

            return final_client_obj
        
        return None
    
    async def set(self, key, value):
        """
        Set an item in the cache.
        """
        for i, cache in enumerate(self.caches):
            if isinstance(cache, InMemoryCache):
                temp = await self._get(key, cache)
            else:
                temp = await self._get(key, cache)
            if temp is not None:
                await self._promote(key, cache, i, value, to_top=True)
                return

        # If the key is not found in any cache, set it in the top cache
        await self._set(key, value, self.caches[0])

    async def _promote(self, key, curr_cache: BaseCache, curr_cache_index: int, value, to_top = False):
        """
        Promote a key/object to a higher priority cache
        """
        print(f"Promoting {key} from cache {curr_cache_index}")
        from models.client import Client
        if curr_cache_index == 0:
            return value, False  # Already in the top cache

        if to_top:
            if not curr_cache.is_db:
                await self._delete(key, curr_cache)
            if isinstance(self.caches[0], InMemoryCache):
                is_newly_created = False
                if 'newly_created' in value and value['newly_created']:
                    is_newly_created = True
                    del value['newly_created']
                client_obj = await Client.from_dict(value)
                new_client_obj_dict = client_obj.to_dict()
                if new_client_obj_dict != value:
                    print(f"[WARN] The client in the db doesn't match created, updating it to match the db")
                    for db in self.dbs:
                        await self._set(key, new_client_obj_dict, db)
                    print(f"[INFO] Updated client {key} to match the db")
                await self._set(key, client_obj, self.caches[0])
                return client_obj, is_newly_created
            else:
                # rendunant atm
                await self._set(key, value, self.caches[0])
            return
        
        new_idx = max(curr_cache_index - 1, 0)
        
        if not curr_cache.is_db:
            await self._delete(key, curr_cache)
        elif isinstance(self.caches[new_idx], InMemoryCache):
            await self._set(key, await Client.from_dict(value), self.caches[new_idx])
        else:
            await self._set(key, value, self.caches[new_idx])

    async def _demote(self, key, curr_cache: BaseCache, curr_cache_index: int, value):
        """
        Demote a key/object to a lower priority cache
        """
        from models.client import Client
        if curr_cache_index == len(self.caches) - 1:
            # Already in the lowest cache
            return

        if not curr_cache.is_db:
            await self._delete(key, curr_cache)
        #await self.caches[curr_cache_index + 1].set(key, value)
        new_idx = min(curr_cache_index + 1, len(self.caches) - 1)
        #print(self.caches[curr_cache_index + 1])
        if isinstance(value, Client):
            await self._set(key, value.to_dict(), self.caches[new_idx])
        else:
            await self._set(key, value, self.caches[new_idx])
                

    async def _get(self, key, cache: BaseCache):
        if inspect.iscoroutinefunction(cache.get):
            return await cache.get(key)
        else:
            return cache.get(key)

    async def _set(self, key, value, cache: BaseCache):
        if inspect.iscoroutinefunction(cache.set):
            await cache.set(key, value)
        else:
            cache.set(key, value)

    async def _delete(self, key, cache: BaseCache): 
        if cache.is_db:
            raise ValueError("Cannot delete from a database cache")
        
        if inspect.iscoroutinefunction(cache.delete):
            await cache.delete(key)
        else:
            cache.delete(key)

    def _start_eviction_loop(self, check_every: int):
        self._eviction_task = asyncio.create_task(self._evict_expired_loop(check_every))

    async def _evict_expired_loop(self, check_every):
        while True:
            await self.evict_expired()
            await asyncio.sleep(check_every)

    async def evict_expired(self):
        for cache in self.caches:
            if hasattr(cache, "all") and not cache.is_db:
                try:
                    all_entries = await cache.all() if inspect.iscoroutinefunction(cache.all) else cache.all()
                    #print(f"ALL ENTRIES IN {cache}: {all_entries}")
                    now = datetime.now().timestamp()
                    entries_to_delete = [(k,v) for k, (v, exp) in all_entries if exp and now > exp]
                    print(f"[INFO] Found {entries_to_delete} expired entries in {cache}")
                    for k,v in entries_to_delete:
                        # if inspect.iscoroutinefunction(cache.delete):
                        #     await cache.delete(k)
                        # else:
                        #     cache.delete(k)
                        await self._demote(k, cache, self.cache_to_index[repr(cache)], v)
                        #await self._delete(k, cache)
                        #print("just checking")
                    print(f"[INFO] Evicted {len(entries_to_delete)} expired entries from {cache}")
                        
                except Exception as e:
                    print(f"[WARN] Failed to evict from {cache}: {e}")
                    continue

    