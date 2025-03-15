import os
import logging
import sqlite3
from pathlib import Path
from collections import namedtuple

# 🔹 Define Persistent Database Path
DB_DIR = Path("/data")
DB_DIR.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
DB_PATH = DB_DIR / "database.db"

# 🔹 NamedTuple for Game Objects
Game = namedtuple("Game", ["id", "url", "name", "activePlayerId"])


class Database:
    def __init__(self, db_file=DB_PATH):
        self.db_file = db_file
        logging.info(f"[DATABASE] Initialized at {self.db_file}")
        self._ensure_tables_exist()

    def _get_connection(self):
        """🔹 Creates a new database connection."""
        return sqlite3.connect(self.db_file)

    def _ensure_tables_exist(self):
        """🔹 Ensures required tables exist on initialization."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_data (
                    discord_id INTEGER PRIMARY KEY,
                    bga_id TEXT UNIQUE NOT NULL
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS game_data (
                    id INTEGER PRIMARY KEY,
                    url TEXT,
                    game_name TEXT,
                    active_player_id INTEGER
                )
            """
            )
            conn.commit()
        logging.info("[DATABASE] Tables checked/created successfully.")

    # ───────────────────────────────────────────────────────────────
    # 🔹 USER MANAGEMENT FUNCTIONS
    # ───────────────────────────────────────────────────────────────

    def insert_user(self, discord_id, bga_id):
        """✅ Adds a new user to the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO user_data (discord_id, bga_id) VALUES (?, ?)",
                    (discord_id, bga_id),
                )
                conn.commit()
            logging.info(f"[DATABASE] User {discord_id} linked to BGA {bga_id}.")
        except sqlite3.IntegrityError:
            logging.warning(f"[DATABASE] User {discord_id} already exists.")

    def delete_user(self, discord_id):
        """❌ Removes a user from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_data WHERE discord_id = ?", (discord_id,))
            conn.commit()
        logging.info(f"[DATABASE] User {discord_id} removed.")

    def get_discord_id_by_bga(self, bga_id):
        """🔍 Finds a Discord ID from a BGA ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT discord_id FROM user_data WHERE bga_id = ?", (bga_id,))
            result = cursor.fetchone()
        return result[0] if result else None

    def get_all_bga_ids(self):
        """🔍 Retrieves all BGA IDs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT bga_id FROM user_data")
            return [row[0] for row in cursor.fetchall()]

    # ───────────────────────────────────────────────────────────────
    # 🔹 GAME MANAGEMENT FUNCTIONS
    # ───────────────────────────────────────────────────────────────

    def getAllGames(self):
        """Retrieve all games."""
        self.connect()
        self.cursor.execute("SELECT id, url, game_name, active_player_id FROM game_data")
        games = self.cursor.fetchall()
        self.close()
        return [Game(*game) for game in games]


    def insert_game(self, game_id, url, game_name, active_player_id):
        """✅ Adds a new game entry."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO game_data (id, url, game_name, active_player_id) VALUES (?, ?, ?, ?)",
                    (game_id, url, game_name, active_player_id),
                )
                conn.commit()
            logging.info(f"[DATABASE] Game {game_id} added ({game_name}).")
        except sqlite3.Error as e:
            logging.error(f"[DATABASE ERROR] {e}")

    def delete_game(self, game_id):
        """❌ Removes a game entry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM game_data WHERE id = ?", (game_id,))
            conn.commit()
        logging.info(f"[DATABASE] Game {game_id} removed.")

    def update_active_player(self, game_id, active_player_id):
        """🔄 Updates the active player for a game."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE game_data SET active_player_id = ? WHERE id = ?",
                (active_player_id, game_id),
            )
            conn.commit()
        logging.info(f"[DATABASE] Game {game_id} updated: Active Player → {active_player_id}.")

    def get_active_player(self, game_id):
        """🔍 Retrieves the active player ID for a game."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT active_player_id FROM game_data WHERE id = ?", (game_id,))
            result = cursor.fetchone()
        return result[0] if result else None

    def get_game_by_id(self, game_id):
        """🔍 Retrieves a game by its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, url, game_name, active_player_id FROM game_data WHERE id = ?", (game_id,))
            result = cursor.fetchone()
        return Game(*result) if result else None

    def get_all_games(self):
        """🔍 Retrieves all games from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, url, game_name, active_player_id FROM game_data")
            return [Game(*row) for row in cursor.fetchall()]
