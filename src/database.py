import sqlite3
import logging
import os
from collections import namedtuple

# ✅ Store SQLite in Railway's persistent directory
DB_PATH = "/data/database.db"

Game = namedtuple("Game", ["id", "url", "name", "activePlayerId"])


class Database:
    def __init__(self):
        os.makedirs("/data", exist_ok=True)  # Ensure the directory exists
        self.db_file = DB_PATH
        self.conn = None
        self.cursor = None

    def connect(self):
        """Open a connection to the database."""
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()

    def createTables(self):
        """Create tables if they don't exist."""
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

    def insertUserData(self, discordId, bgaId):
        """Insert a user into the database."""
        self.connect()
        try:
            self.cursor.execute(
                "INSERT INTO user_data (discord_id, bga_id) VALUES (?, ?)",
                (discordId, bgaId),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            logging.error(f"User with Discord ID {discordId} already exists.")
        finally:
            self.close()

    def deleteUserData(self, discord_id):
        """Remove a user from the database."""
        self.connect()
        self.cursor.execute("DELETE FROM user_data WHERE discord_id = ?", (discord_id,))
        self.conn.commit()
        self.close()

    def getDiscordIdByBgaId(self, bga_id):
        """Retrieve a Discord ID by BGA ID."""
        self.connect()
        self.cursor.execute(
            "SELECT discord_id FROM user_data WHERE bga_id = ?", (bga_id,)
        )
        result = self.cursor.fetchone()
        self.close()
        return result[0] if result else None

    def insertGameData(self, id, url, gameName, activePlayerId):
        """Insert a new game into the database."""
        self.connect()
        try:
            self.cursor.execute(
                "INSERT INTO game_data (id, url, game_name, active_player_id) VALUES (?, ?, ?, ?)",
                (id, url, gameName, activePlayerId),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"SQLite error: {e}")
        finally:
            self.close()

    def deleteGameData(self, id):
        """Remove a game from the database."""
        self.connect()
        self.cursor.execute("DELETE FROM game_data WHERE id = ?", (id,))
        self.conn.commit()
        self.close()

    def updateActivePlayer(self, id, activePlayerId):
        """Update the active player of a game."""
        self.connect()
        self.cursor.execute(
            "UPDATE game_data SET active_player_id = ? WHERE id = ?",
            (activePlayerId, id),
        )
        self.conn.commit()
        self.close()

    def getActivePlayer(self, id):
        """Retrieve the active player of a game."""
        self.connect()
        self.cursor.execute("SELECT active_player_id FROM game_data WHERE id = ?", (id,))
        result = self.cursor.fetchone()
        self.close()
        return result[0] if result else None

    def getGameById(self, game_id):
        """Retrieve a game by its ID."""
        self.connect()
        self.cursor.execute(
            "SELECT id, url, game_name, active_player_id FROM game_data WHERE id = ?",
            (game_id,),
        )
        result = self.cursor.fetchone()
        self.close()
        return Game(*result) if result else None

    def getAllGames(self):
        """Retrieve all games."""
        self.connect()
        self.cursor.execute("SELECT id, url, game_name, active_player_id FROM game_data")
        games = self.cursor.fetchall()
        self.close()
        return [Game(*game) for game in games]

    def getAllBgaIds(self):
        """Retrieve all BGA IDs."""
        self.connect()
        self.cursor.execute("SELECT bga_id FROM user_data")
        rows = self.cursor.fetchall()
        self.close()
        return [row[0] for row in rows]

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
