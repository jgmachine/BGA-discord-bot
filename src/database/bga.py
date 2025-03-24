import logging
from typing import Optional, List
from dataclasses import dataclass
from .core import DatabaseConnection

logger = logging.getLogger(__name__)

@dataclass
class Game:
    id: str
    url: str
    name: str
    activePlayerId: str

class BGADatabase:
    """BGA specific database operations."""

    def __init__(self, db_connection):
        self.db = db_connection

    def insert_game_data(self, id: str, url: str, name: str, active_player_id: str) -> bool:
        """Adds or updates a game entry."""
        with self.db:
            try:
                self.db.cursor.execute(
                    """INSERT OR REPLACE INTO game_data 
                       (id, url, game_name, active_player_id) 
                       VALUES (?, ?, ?, ?)""",
                    (id, url, name, active_player_id)
                )
                return True
            except Exception as e:
                logger.error(f"Failed to insert game: {e}")
                return False

    def get_game_by_id(self, game_id: str) -> Optional[Game]:
        """Retrieves a game by ID."""
        with self.db:
            try:
                self.db.cursor.execute(
                    """SELECT id, url, game_name, active_player_id 
                       FROM game_data WHERE id = ?""",
                    (game_id,)
                )
                result = self.db.cursor.fetchone()
                return Game(*result) if result else None
            except Exception as e:
                logger.error(f"Failed to get game: {e}")
                return None

    def get_all_games(self) -> List[Game]:
        """Retrieves all active games."""
        with self.db:
            try:
                self.db.cursor.execute(
                    "SELECT id, url, game_name, active_player_id FROM game_data"
                )
                return [Game(*game) for game in self.db.cursor.fetchall()]
            except Exception as e:
                logger.error(f"Failed to get games: {e}")
                return []
