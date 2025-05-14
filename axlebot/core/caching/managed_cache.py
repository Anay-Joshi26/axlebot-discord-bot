from typing import List
from core.caching.base_cache import BaseCache
from core.caching.caches import InMemoryCache, RedisCache, FirestoreCache

class CacheManager:
    """
    A class to manage a caches
    """
    def __init__(self, caches: List[BaseCache]):
        print(caches)
        self.caches = sorted(caches, key=lambda c: c.priority)

    @property
    def active_cache(self) -> BaseCache:
        """
        Returns the active cache (the one with the highest priority).
        """
        return self.caches[0]

    async def get(self, key) -> dict|None:
        """
        Get an item from the cache.
        """
        key = str(key)
        for i, cache in enumerate(self.caches):
            #print(cache)
            if isinstance(cache, InMemoryCache):
                print("InMemoryCache...........")
                try:
                    value = cache.sync_get(key)
                    print("ID value", id(value))
                except Exception as e:
                    print(f"Exception in sync_get: {e}")
                    raise
                print(value)
            else:
                value = await cache.get(key)
            print(f"Cache {i}: {cache}\nKey: {key}\nValue: {value}")
            if value is None:
                print('aaa')
                continue
            
            final_client_obj = await self._promote(key, cache, i, value, to_top=True)

            return final_client_obj
        
        return None
    
    async def set(self, key, value):
        """
        Set an item in the cache.
        """
        for i, cache in enumerate(self.caches):
            if isinstance(cache, InMemoryCache):
                temp = cache.sync_get(key)
            else:
                temp = await cache.get(key)
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
            # Already in the top cache
            return value

        if to_top:
            print("Promoting to top cache")
            if not curr_cache.is_db:
                await curr_cache.delete(key)
            if isinstance(self.caches[0], InMemoryCache):
                client_obj = await Client.from_dict(value)
                print("client_obj", client_obj)
                self.caches[0].set(key, client_obj)

                print("Set client_obj id:", id(client_obj))
                print("Get client_obj id:", id(self.caches[0].sync_get(key)))
                return client_obj

            else:
                # rendunant atm
                await self.caches[0].set(key, value)
            return
        
        if not curr_cache.is_db:
            await curr_cache.delete(key)
        elif isinstance(self.caches[curr_cache_index - 1], InMemoryCache):
            self.caches[curr_cache_index - 1].set(key, await Client.from_dict(value))
        else:
            await self.caches[curr_cache_index - 1].set(key, value)

    async def _demote(self, key, curr_cache: BaseCache, curr_cache_index: int, value):
        """
        Demote a key/object to a lower priority cache
        """
        if curr_cache_index == len(self.caches) - 1:
            # Already in the lowest cache
            return

        if not curr_cache.is_db:
            await curr_cache.delete(key)
        await self.caches[curr_cache_index + 1].set(key, value)
                

    async def _get(self, key, cache: BaseCache):
        return await cache.get(key)

    async def _set(self, key, value, cache: BaseCache):
        await cache.set(key, value)

    async def _delete(self, key, cache: BaseCache): 
        await cache.delete(key)
    