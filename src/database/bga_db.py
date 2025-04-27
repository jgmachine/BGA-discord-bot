import logging
import sqlite3
from collections import namedtuple
from .base import BaseDatabase

Game = namedtuple("Game", ["id", "url", "name", "activePlayerId"])

class BGADatabase(BaseDatabase):
    """BGA-specific database operations."""

    def create_tables(self):
        """Creates BGA-related tables and handles migrations."""
        # First create tables if they don't exist
        self._execute("""
            CREATE TABLE IF NOT EXISTS user_data (
                discord_id INTEGER PRIMARY KEY,
                bga_id TEXT UNIQUE NOT NULL
            )
        """)
        
        # Check if dm_enabled column exists
        cursor = self._execute("PRAGMA table_info(user_data)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Add dm_enabled column if it doesn't exist
        if 'dm_enabled' not in columns:
            self._execute("ALTER TABLE user_data ADD COLUMN dm_enabled INTEGER DEFAULT 0")
            logging.info("[DATABASE] Added dm_enabled column to user_data table")
        
        # Create game_data table
        self._execute("""
            CREATE TABLE IF NOT EXISTS game_data (
                id INTEGER PRIMARY KEY,
                url TEXT,
                game_name TEXT,
                active_player_id INTEGER
            )
        """)
        logging.info("[DATABASE] BGA tables checked/created successfully.")

    def set_dm_preference(self, discord_id: int, enabled: bool):
        """Set DM preference for a user."""
        self._execute(
            "UPDATE user_data SET dm_enabled = ? WHERE discord_id = ?",
            (1 if enabled else 0, discord_id)
        )
        logging.info(f"[DATABASE] User {discord_id} DM preference set to {enabled}")

    def get_dm_preference(self, discord_id: int) -> bool:
        """Get DM preference for a user."""
        results = self._execute(
            "SELECT dm_enabled FROM user_data WHERE discord_id = ?",
            (discord_id,)
        )
        return bool(results[0][0]) if results else False

    # User Management
    def insert_user_data(self, discord_id, bga_id):
        """Adds a new user to the database."""
        try:
            self._execute(
                "INSERT INTO user_data (discord_id, bga_id) VALUES (?, ?)",
                (discord_id, bga_id)
            )
            logging.info(f"[DATABASE] User {discord_id} linked to BGA {bga_id}.")
        except sqlite3.IntegrityError:
            logging.warning(f"[DATABASE] User {discord_id} already exists.")

    def delete_user_data(self, discord_id):
        """Removes a user from the database."""
        self._execute("DELETE FROM user_data WHERE discord_id = ?", (discord_id,))
        logging.info(f"[DATABASE] User {discord_id} removed.")

    def get_discord_id_by_bga_id(self, bga_id):
        """Finds a Discord ID from a BGA ID."""
        results = self._execute(
            "SELECT discord_id FROM user_data WHERE bga_id = ?", 
            (bga_id,)
        )
        return results[0][0] if results else None

    def get_all_bga_ids(self):
        """Retrieves all BGA IDs."""
        results = self._execute("SELECT bga_id FROM user_data")
        return [row[0] for row in results] if results else []

    # Game Management
    def insert_game_data(self, id, url, game_name, active_player_id):
        """Adds a new game entry."""
        try:
            self._execute(
                "INSERT INTO game_data (id, url, game_name, active_player_id) VALUES (?, ?, ?, ?)",
                (id, url, game_name, active_player_id)
            )
            logging.info(f"[DATABASE] Game {id} added ({game_name}).")
        except sqlite3.Error as e:
            logging.error(f"[DATABASE ERROR] {e}")

    def delete_game_data(self, id):
        """Removes a game entry."""
        self._execute("DELETE FROM game_data WHERE id = ?", (id,))
        logging.info(f"[DATABASE] Game {id} removed.")

    def update_active_player(self, id, active_player_id):
        """Updates the active player for a game."""
        self._execute(
            "UPDATE game_data SET active_player_id = ? WHERE id = ?",
            (active_player_id, id)
        )
        logging.info(f"[DATABASE] Game {id} updated: Active Player → {active_player_id}.")

    def get_active_player(self, id):
        """Retrieves the active player ID for a game."""
        results = self._execute("SELECT active_player_id FROM game_data WHERE id = ?", (id,))
        return results[0][0] if results else None

    def get_game_by_id(self, game_id):
        """Retrieves a game by its ID."""
        results = self._execute(
            "SELECT id, url, game_name, active_player_id FROM game_data WHERE id = ?",
            (game_id,)
        )
        return Game(*results[0]) if results else None

    def get_all_games(self):
        """Retrieves all games from the database."""
        results = self._execute("SELECT id, url, game_name, active_player_id FROM game_data")
        return [Game(*game) for game in results] if results else []
