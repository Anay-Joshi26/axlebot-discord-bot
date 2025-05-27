import asyncio
from typing import Dict, Any, Union
from firebase_admin import firestore
from firebase_admin.firestore import DocumentSnapshot, CollectionReference
from firebase_admin import firestore_async
from google.cloud.firestore_v1.async_client import AsyncClient
from google.cloud.firestore_v1.collection import CollectionReference
from google.cloud.firestore_v1.client import Client


class FirebaseClient:
    def __init__(self, db: AsyncClient):
        self.guild_ref: CollectionReference = db.collection("guilds")
        
    def get_default_data_dict(self, guild_id):
        return {
                "guild_id": guild_id,
                "max_concurrent_song_loadings": 2,
                "playlists": [],
                "acceptable_delay": 5,
                "is_premium": False
            }


    async def get_client_dict(self, guild_id: Union[int, str]) -> Dict[str, Any]:
        if isinstance(guild_id, int):
            guild_id = str(guild_id)

        data: DocumentSnapshot = await self.guild_ref.document(guild_id).get()

        if not data.exists:
            default_data = self.get_default_data_dict(guild_id)
            await self.set_data_for_client(guild_id, default_data)
            default_data['newly_created'] = True  # Indicate that this is a newly created document
            return default_data

        return data.to_dict()

    async def set_data_for_client(self, guild_id: Union[int, str], data: Dict[str, Any]) -> None:
        if isinstance(guild_id, int):
            guild_id = str(guild_id)

        await self.guild_ref.document(guild_id).set(data)

    async def set_data_attribute_for_client(self, guild_id: Union[int, str], attribute: str, value: Any) -> None:
        if isinstance(guild_id, int):
            guild_id = str(guild_id)

        await self.guild_ref.document(guild_id).update({attribute: value})
