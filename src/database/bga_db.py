import logging
import sqlite3
from collections import namedtuple
from .base import BaseDatabase

Game = namedtuple("Game", ["id", "url", "name", "activePlayerId"])

class BGADatabase(BaseDatabase):
    """BGA-specific database operations."""

    def create_tables(self):
        """Creates BGA-related tables."""
        self._execute("""
            CREATE TABLE IF NOT EXISTS user_data (
                discord_id INTEGER PRIMARY KEY,
                bga_id TEXT UNIQUE NOT NULL
            )
        """)
        self._execute("""
            CREATE TABLE IF NOT EXISTS game_data (
                id INTEGER PRIMARY KEY,
                url TEXT,
                game_name TEXT,
                active_player_id INTEGER
            )
        """)
        logging.info("[DATABASE] BGA tables checked/created successfully.")

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
        cursor = self._execute("SELECT discord_id FROM user_data WHERE bga_id = ?", (bga_id,)))
        result = cursor.fetchone()sults else None
        return result[0] if result else None
    def get_all_bga_ids(self):
    def get_all_bga_ids(self):Ds."""
        """Retrieves all BGA IDs."""ECT bga_id FROM user_data")
        results = self._execute("SELECT bga_id FROM user_data")
        # results is already a list of tuples from fetchall()
        return [row[0] for row in results] if results else []
    # Game Management
    # Game Managementata(self, id, url, game_name, active_player_id):
    def insert_game_data(self, id, url, game_name, active_player_id):
        """Adds a new game entry."""
        try:self._execute(
            self._execute(TO game_data (id, url, game_name, active_player_id) VALUES (?, ?, ?, ?)",
                "INSERT INTO game_data (id, url, game_name, active_player_id) VALUES (?, ?, ?, ?)",
                (id, url, game_name, active_player_id)
            )ogging.info(f"[DATABASE] Game {id} added ({game_name}).")
            logging.info(f"[DATABASE] Game {id} added ({game_name}).")
        except sqlite3.Error as e:ASE ERROR] {e}")
            logging.error(f"[DATABASE ERROR] {e}")
    def delete_game_data(self, id):
    def delete_game_data(self, id):
        """Removes a game entry."""game_data WHERE id = ?", (id,))
        self._execute("DELETE FROM game_data WHERE id = ?", (id,))
        logging.info(f"[DATABASE] Game {id} removed.")
    def update_active_player(self, id, active_player_id):
    def update_active_player(self, id, active_player_id):
        """Updates the active player for a game."""
        self._execute(me_data SET active_player_id = ? WHERE id = ?",
            "UPDATE game_data SET active_player_id = ? WHERE id = ?",
            (active_player_id, id)
        )ogging.info(f"[DATABASE] Game {id} updated: Active Player → {active_player_id}.")
        logging.info(f"[DATABASE] Game {id} updated: Active Player → {active_player_id}.")
    def get_active_player(self, id):
    def get_active_player(self, id):er ID for a game."""
        """Retrieves the active player ID for a game.""" FROM game_data WHERE id = ?", (id,))
        cursor = self._execute("SELECT active_player_id FROM game_data WHERE id = ?", (id,))
        result = cursor.fetchone()
        return result[0] if result else None
        """Retrieves a game by its ID."""
    def get_game_by_id(self, game_id):
            "SELECT id, url, game_name, active_player_id FROM game_data WHERE id = ?",
        results = self._execute(
            "SELECT id, url, game_name, active_player_id FROM game_data WHERE id = ?",
            (game_id,)r.fetchone()
        )eturn Game(*result) if result else None
        return Game(*results[0]) if results else None

    def get_all_games(self):        """Retrieves all games from the database."""
        """Retrieves all games from the database."""te("SELECT id, url, game_name, active_player_id FROM game_data")
        results = self._execute("SELECT id, url, game_name, active_player_id FROM game_data")nnection closes
        return [Game(*game) for game in results] if results else []
