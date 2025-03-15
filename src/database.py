import os
import logging
import sqlite3
from pathlib import Path
from collections import namedtuple

# 🔹 Ensure the /data directory exists for persistent storage
DB_DIR = Path("/data")
DB_DIR.mkdir(parents=True, exist_ok=True)  # Ensures the directory exists
DB_PATH = DB_DIR / "database.db"

# 🔹 NamedTuple for Game Objects
Game = namedtuple("Game", ["id", "url", "name", "activePlayerId"])


class Database:
    def __init__(self, db_file=DB_PATH):
        self.db_file = db_file
        self.conn = None
        self.cursor = None

        # Log the database path for debugging
        logging.info(f"[DATABASE] Initialized at: {self.db_file}")

        # Ensure tables exist on startup
        self.createTables()

    def connect(self):
        """🔹 Establishes a connection to the SQLite database."""
        logging.info(f"[DATABASE] Connecting to database at: {self.db_file}")
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()

    def createTables(self):
        """🔹 Creates tables if they don't exist."""
        self.connect()
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_data (
                discord_id INTEGER PRIMARY KEY,
                bga_id TEXT UNIQUE NOT NULL
            )
        """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS game_data (
                id INTEGER PRIMARY KEY,
                url TEXT,
                game_name TEXT,
                active_player_id INTEGER
            )
        """
        )
        self.conn.commit()
        self.close()
        logging.info("[DATABASE] Tables checked/created successfully.")

    # ───────────────────────────────────────────────────────────────
    # 🔹 USER MANAGEMENT FUNCTIONS
    # ───────────────────────────────────────────────────────────────

    def insertUserData(self, discordId, bgaId):
        """✅ Adds a new user to the database."""
        self.connect()
        try:
            self.cursor.execute(
                "INSERT INTO user_data (discord_id, bga_id) VALUES (?, ?)",
                (discordId, bgaId),
            )
            self.conn.commit()
            logging.info(f"[DATABASE] User {discordId} linked to BGA {bgaId}.")
        except sqlite3.IntegrityError:
            logging.warning(f"[DATABASE] User {discordId} already exists.")
        finally:
            self.close()

    def deleteUserData(self, discord_id):
        """❌ Removes a user from the database."""
        self.connect()
        self.cursor.execute("DELETE FROM user_data WHERE discord_id = ?", (discord_id,))
        self.conn.commit()
        self.close()
        logging.info(f"[DATABASE] User {discord_id} removed.")

    def getDiscordIdByBgaId(self, bga_id):
        """🔍 Finds a Discord ID from a BGA ID."""
        self.connect()
        self.cursor.execute(
            "SELECT discord_id FROM user_data WHERE bga_id = ?", (bga_id,)
        )
        result = self.cursor.fetchone()
        self.close()
        return result[0] if result else None

    def getAllBgaIds(self):
        """🔍 Retrieves all BGA IDs."""
        self.connect()
        self.cursor.execute("SELECT bga_id FROM user_data")
        rows = self.cursor.fetchall()
        self.close()
        return [row[0] for row in rows]

    # ───────────────────────────────────────────────────────────────
    # 🔹 GAME MANAGEMENT FUNCTIONS
    # ───────────────────────────────────────────────────────────────

    def insertGameData(self, id, url, gameName, activePlayerId):
        """✅ Adds a new game entry."""
        self.connect()
        try:
            self.cursor.execute(
                "INSERT INTO game_data (id, url, game_name, active_player_id) VALUES (?, ?, ?, ?)",
                (id, url, gameName, activePlayerId),
            )
            self.conn.commit()
            logging.info(f"[DATABASE] Game {id} added ({gameName}).")
        except sqlite3.Error as e:
            logging.error(f"[DATABASE ERROR] {e}")
        finally:
            self.close()

    def deleteGameData(self, id):
        """❌ Removes a game entry."""
        self.connect()
        self.cursor.execute("DELETE FROM game_data WHERE id = ?", (id,))
        self.conn.commit()
        self.close()
        logging.info(f"[DATABASE] Game {id} removed.")

    def updateActivePlayer(self, id, activePlayerId):
        """🔄 Updates the active player for a game."""
        self.connect()
        self.cursor.execute(
            "UPDATE game_data SET active_player_id = ? WHERE id = ?",
            (activePlayerId, id),
        )
        self.conn.commit()
        self.close()
        logging.info(f"[DATABASE] Game {id} updated: Active Player → {activePlayerId}.")

    def getActivePlayer(self, id):
        """🔍 Retrieves the active player ID for a game."""
        self.connect()
        self.cursor.execute("SELECT active_player_id FROM game_data WHERE id = ?", (id,))
        result = self.cursor.fetchone()
        self.close()
        return result[0] if result else None

    def getGameById(self, game_id):
        """🔍 Retrieves a game by its ID."""
        self.connect()
        self.cursor.execute(
            "SELECT id, url, game_name, active_player_id FROM game_data WHERE id = ?",
            (game_id,),
        )
        result = self.cursor.fetchone()
        self.close()
        return Game(*result) if result else None

    def getAllGames(self):
        """🔍 Retrieves all games from the database."""
        self.connect()
        self.cursor.execute("SELECT id, url, game_name, active_player_id FROM game_data")
        games = self.cursor.fetchall()
        self.close()
        return [Game(*game) for game in games]

    def close(self):
        """🔹 Closes the database connection."""
        if self.conn:
            self.conn.close()
            logging.info("[DATABASE] Connection closed.")
