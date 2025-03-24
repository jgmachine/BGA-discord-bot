from collections import namedtuple
from .core import DatabaseConnection

Game = namedtuple("Game", ["id", "url", "name", "activePlayerId"])

class BGADatabase(DatabaseConnection):
    """BGA specific database operations."""

    def insert_game_data(self, id, url, game_name, active_player_id):
        """Adds a new game entry."""
        with self:
            self.cursor.execute(
                """INSERT INTO game_data 
                   (id, url, game_name, active_player_id) 
                   VALUES (?, ?, ?, ?)""",
                (id, url, game_name, active_player_id)
            )
            self.conn.commit()

    def get_game_by_id(self, game_id):
        """Retrieves a game by ID."""
        with self:
            self.cursor.execute(
                """SELECT id, url, game_name, active_player_id 
                   FROM game_data WHERE id = ?""",
                (game_id,)
            )
            result = self.cursor.fetchone()
            return Game(*result) if result else None

    # ... other BGA-specific methods ...
