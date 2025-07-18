from collections.abc import Iterable
import core.extensions

class ServerConfig:
    def __init__(self, client):
        """
        Initialise the Permissions object for a client.

        :param client: A client object.
        """
        self.client = client
        self.permitted_roles_of_use = set()
        self.permitted_channels_of_use = set()
        self.delete_message_after_play = True
        self.MAX_PERMITTED_ROLES = 10
        self.MAX_PERMITTED_CHANNELS = 10
        self.auto_play = False # Never keeps the queue empty, always recommends a song to play next

    async def _trigger_update(self):
        await self.client.update_changes_by_attribute("server_config", self.to_dict())

    async def update_auto_play(self, value: bool, update_db: bool = True):
        """
        Sets whether to automatically play a song when the queue is empty.
        This is useful for servers that want to keep the music playing without user intervention.
        New music is served up based on recommendations on the queue of music.

        :param value: True to enable auto play, False to disable.
        """
        self.auto_play = value
        if update_db:
            await self._trigger_update()

    async def add_permitted_role(self, role_id: int, update_db: bool = True):
        """
        Adds a role ID to the permitted roles of use.

        :param role_id: The ID of the role to add.
        """
        if len(self.permitted_roles_of_use) >= self.MAX_PERMITTED_ROLES:
            raise ValueError(f"Cannot add more than {self.MAX_PERMITTED_ROLES} roles. Please remove some before adding new ones.")
        
        self.permitted_roles_of_use.add(role_id)
        if update_db:
            await self._trigger_update()

    async def remove_permitted_role(self, role_id: int, update_db: bool = True):
        """
        Removes a role ID from the permitted roles of use.

        :param role_id: The ID of the role to remove.
        """
        self.permitted_roles_of_use.discard(role_id)
        if update_db:
            await self._trigger_update()

    async def add_permitted_channel(self, channel_id: int, update_db: bool = True):
        """
        Adds a channel ID to the permitted channels of use.

        :param channel_id: The ID of the channel to add.
        """
        if len(self.permitted_channels_of_use) >= self.MAX_PERMITTED_CHANNELS:
            raise ValueError(f"Cannot add more than {self.MAX_PERMITTED_CHANNELS} channels. Please remove some before adding new ones.")
        
        self.permitted_channels_of_use.add(channel_id)
        if update_db:
            await self._trigger_update()

    async def remove_permitted_channel(self, channel_id: int, update_db: bool = True):
        """
        Removes a channel ID from the permitted channels of use.

        :param channel_id: The ID of the channel to remove.
        """
        self.permitted_channels_of_use.discard(channel_id)
        if update_db:
            await self._trigger_update()  

    async def set_delete_message_after_play(self, value: bool, update_db: bool = True):
        """
        Sets whether to delete the message after playing.

        :param value: True to delete the message after play, False otherwise.
        """
        self.delete_message_after_play = value
        if update_db:
            await self._trigger_update()

    def __repr__(self):
        return (f"ServerConfig(permitted_roles_of_use={self.permitted_roles_of_use}, "
                f"permitted_channels_of_use={self.permitted_channels_of_use}, "
                f"delete_message_after_play={self.delete_message_after_play})")
    
    @staticmethod
    def get_default_config_dict() -> dict:
        """
        Returns a default configuration dictionary for the server.

        :return: A dictionary with default configuration values.
        """
        return {
            "permitted_roles_of_use": [],
            "permitted_channels_of_use": [],
            "delete_message_after_play": False,
            "MAX_PERMITTED_ROLES": 10,
            "MAX_PERMITTED_CHANNELS": 10,
            "auto_play": False
        }

    def to_dict(self) -> dict:
        """
        Converts the object to a dictionary representation,
        automatically handling sets, tuples, etc.

        :return: A dictionary of the object's attributes.
        """
        def convert(value):
            if isinstance(value, str) or isinstance(value, dict):
                return value
            elif isinstance(value, Iterable):
                return list(value)
            elif isinstance(value, int) or isinstance(value, float) or isinstance(value, bool) or value is None:
                return value
            else:
                raise TypeError(f"Unsupported type: {type(value)}")

        return {k: convert(v) for k, v in self.__dict__.items() if k != "client"}
    
    @classmethod
    def from_dict(cls, data: dict, client) -> "ServerConfig":
        """
        Dynamically creates an instance from a dictionary.
        Converts lists back to sets and removes any invalid (deleted) roles/channels.
        """
        obj = cls(client)

        guild = core.extensions.bot.get_guild(int(client.server_id))  # Get the current guild object

        for key, value in data.items():
            if not hasattr(obj, key):
                continue

            original_type = type(getattr(obj, key))

            if original_type is set and isinstance(value, list):
                print(value)
                filtered = set(value)

                if key == "permitted_channels_of_use":
                    # Remove channel IDs that no longer exist
                    filtered = {cid for cid in filtered if guild.get_channel(cid) is not None}

                elif key == "permitted_roles_of_use":
                    # Remove role IDs that no longer exist
                    filtered = {rid for rid in filtered if guild.get_role(rid) is not None}

                setattr(obj, key, filtered)

            else:
                setattr(obj, key, value)

        return obj
