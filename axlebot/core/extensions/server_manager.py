from core.server_manager import ServerManager
from core.extensions import cache_manager

server_manager = ServerManager(cache_manager=cache_manager)


