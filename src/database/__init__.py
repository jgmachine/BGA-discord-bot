from pathlib import Path
from typing import Dict, List, Optional
from .core import DatabaseConnection
from .hosting import HostDatabase
from .bga import BGADatabase, Game

class Database:
    """Main database interface combining all functionality."""
    def __init__(self, db_file: Path = Path("/data/database.db")):
        self._connection = DatabaseConnection(db_file)
        self._hosting = HostDatabase(self._connection)
        self._bga = BGADatabase(self._connection)

    # Core operations
    def create_tables(self) -> None:
        """Initializes all database tables."""
        self._connection.create_tables()

    # Host operations
    def add_host(self, discord_id: str, username: str) -> bool:
        return self._hosting.add_host(discord_id, username)

    def remove_host(self, discord_id: str) -> bool:
        return self._hosting.remove_host(discord_id)

    def get_next_host(self) -> Optional[Dict[str, str]]:
        return self._hosting.get_next_host()

    def get_all_hosts(self) -> List[Dict[str, any]]:
        return self._hosting.get_all_hosts()

    def rotate_hosts(self) -> bool:
        return self._hosting.rotate_hosts()

    # BGA operations
    def insert_game_data(self, id: str, url: str, name: str, active_player_id: str) -> bool:
        return self._bga.insert_game_data(id, url, name, active_player_id)

    def get_game_by_id(self, game_id: str) -> Optional[Game]:
        return self._bga.get_game_by_id(game_id)

    def get_all_games(self) -> List[Game]:
        return self._bga.get_all_games()
