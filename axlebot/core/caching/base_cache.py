from abc import ABC, abstractmethod
from datetime import timedelta
import asyncio


class BaseCache(ABC):
    """
    Base class for caching mechanisms.
    """
    def __init__(self, priority: int, ttl: timedelta, is_db = False):
        """
        Initializes the cache.
        """
        self.priority = priority
        self.ttl = None if is_db else ttl # Time to live for cache items, if None, the item will never expire
        self.is_db = is_db # Whether the cache is a database or not, if it is, it will not be deleted from
        #self.cleanup_task = asyncio.create_task(self._evict_expired(timedelta(minutes=check_freq_time)))

    @abstractmethod
    async def get(self, key):
        """
        Retrieves an item from the cache.
        :param key: The key of the item to retrieve.
        :return: The cached item or None if not found.
        """
        raise NotImplementedError("Subclasses must implement this method.")
    
    @abstractmethod
    async def all(self):
        """
        Returns every entry within the cache
        """
        raise NotImplementedError("Subclasses must implement this method.")


    @abstractmethod
    async def set(self, key: str, value):
        """
        Stores an item in the cache.
        :param key: The key to store the item under.
        :param value: The item to store.
        """
        raise NotImplementedError("Subclasses must implement this method.")
    
    @abstractmethod
    async def delete(self, key: str):
        """
        Deletes an item from the cache.
        :param key: The key of the item to delete.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def __repr__(self):
        return f"{self.__class__.__name__}"