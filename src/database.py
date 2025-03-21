import os
import logging
import sqlite3
from pathlib import Path
from collections import namedtuple

# 🔹 Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log'  # Main log file for all operations
)

# Create a specific logger for hosting rotation functions
host_logger = logging.getLogger('hosting_rotation')
file_handler = logging.FileHandler('hosting_rotation.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
host_logger.addHandler(file_handler)
host_logger.setLevel(logging.INFO)

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
        self.createHostingTable()
        self.conn.commit()
        self.close()
        logging.info("[DATABASE] Tables checked/created successfully.")

    # Alias with snake_case naming convention
    def create_tables(self):
        """Alias for createTables using snake_case naming convention."""
        return self.createTables()

    # ───────────────────────────────────────────────────────────────
    # 🔹 HOSTING ROTATION FUNCTIONS
    # ───────────────────────────────────────────────────────────────
    def createHostingTable(self):
        """🔹 Creates the hosting rotation table if it doesn't exist."""
        host_logger.info("Creating hosting rotation table if it doesn't exist")
        try:
            self.cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS hosting_rotation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id TEXT UNIQUE NOT NULL,
                    username TEXT NOT NULL,
                    order_position INTEGER NOT NULL,
                    last_hosted DATE,
                    active INTEGER DEFAULT 1
                )
                '''
            )
            host_logger.info("Hosting rotation table created or already exists")
        except Exception as e:
            host_logger.error(f"Error creating hosting rotation table: {e}")
            raise

    # Alias with snake_case naming convention
    def create_hosting_table(self):
        """Alias for createHostingTable using snake_case naming convention."""
        return self.createHostingTable()

    def addHost(self, discord_id, username):
        """Adds a user to the hosting rotation."""
        host_logger.info(f"Adding host: discord_id={discord_id}, username={username}")
        try:
            self.connect()
            cursor = self.cursor
            # Get the next available order position
            cursor.execute("SELECT MAX(order_position) FROM hosting_rotation")
            result = cursor.fetchone()
            max_pos = result[0] if result and result[0] is not None else 0
            next_position = max_pos + 1
            
            host_logger.debug(f"Next position calculated as {next_position}")
            
            cursor.execute("INSERT OR IGNORE INTO hosting_rotation (discord_id, username, order_position) VALUES (?, ?, ?)",
                        (discord_id, username, next_position))
            
            self.conn.commit()
            rows_affected = cursor.rowcount
            host_logger.info(f"Host added successfully, rows affected: {rows_affected}")
            self.close()
            return rows_affected
        except Exception as e:
            host_logger.error(f"Error adding host: {e}")
            self.conn.rollback()
            self.close()
            raise

    # Alias with snake_case naming convention
    def add_host(self, discord_id, username):
        """Alias for addHost using snake_case naming convention."""
        return self.addHost(discord_id, username)

    def getNextHost(self):
        """Fetches the next user in the hosting rotation."""
        host_logger.info("Fetching next host")
        try:
            self.connect()
            cursor = self.cursor
            
            cursor.execute("SELECT discord_id, username FROM hosting_rotation WHERE active=1 ORDER BY order_position ASC LIMIT 1")
            next_host = cursor.fetchone()
            self.close()
            
            if next_host:
                host_logger.info(f"Next host found: {next_host[1]}")
                return {"discord_id": next_host[0], "username": next_host[1]}
            else:
                host_logger.warning("No active hosts found in rotation")
                return None
        except Exception as e:
            host_logger.error(f"Error fetching next host: {e}")
            self.close()
            raise

    # Alias with snake_case naming convention
    def get_next_host(self):
        """Alias for getNextHost using snake_case naming convention."""
        return self.getNextHost()

    def rotateHosts(self):
        """Moves the current host to the back of the queue."""
        host_logger.info("Rotating hosts")
        try:
            self.connect()
            cursor = self.cursor
            # Get the current host
            cursor.execute("SELECT discord_id, username, order_position FROM hosting_rotation WHERE active=1 ORDER BY order_position ASC LIMIT 1")
            host = cursor.fetchone()
            if not host:
                host_logger.warning("No active hosts found for rotation")
                self.close()
                return "No active hosts found."
                
            host_id, host_name, host_position = host
            host_logger.info(f"Current host: {host_name} (position {host_position})")
            
            # Update last_hosted date for the current host
            cursor.execute("UPDATE hosting_rotation SET last_hosted = DATE('now') WHERE discord_id = ?", (host_id,))
            
            # Move the host to the back
            cursor.execute("UPDATE hosting_rotation SET order_position = order_position - 1 WHERE order_position > ?", (host_position,))
            cursor.execute("SELECT MAX(order_position) FROM hosting_rotation")
            max_pos = cursor.fetchone()[0] or 0
            cursor.execute("UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ?", (max_pos, host_id,))
            
            self.conn.commit()
            host_logger.info(f"Host {host_name} rotated to position {max_pos}")
            self.close()
            return f"Rotated: {host_name} moved to the end of the queue"
        except Exception as e:
            host_logger.error(f"Error rotating hosts: {e}")
            self.conn.rollback()
            self.close()
            raise

    # Alias with snake_case naming convention
    def rotate_hosts(self):
        """Alias for rotateHosts using snake_case naming convention."""
        return self.rotateHosts()

    def deferHost(self, discord_id):
        """Keeps a host at the top until the next available date."""
        host_logger.info(f"Deferring host with discord_id={discord_id}")
        try:
            self.connect()
            cursor = self.cursor
            
            # Verify the host exists and is active
            cursor.execute("SELECT username FROM hosting_rotation WHERE discord_id=? AND active=1", (discord_id,))
            host = cursor.fetchone()
            if not host:
                host_logger.warning(f"Host with discord_id={discord_id} not found or not active")
                self.close()
                return "Host not found or not active"
                
            # Keep them at the top, move others forward
            cursor.execute("UPDATE hosting_rotation SET order_position = order_position + 1 WHERE discord_id != ? AND active=1", (discord_id,))
            cursor.execute("UPDATE hosting_rotation SET order_position = 1 WHERE discord_id = ?", (discord_id,))
            
            self.conn.commit()
            host_logger.info(f"Host {host[0]} deferred successfully")
            self.close()
            return f"Deferred: {host[0]} kept at the top of the queue"
        except Exception as e:
            host_logger.error(f"Error deferring host: {e}")
            self.conn.rollback()
            self.close()
            raise

    # Alias with snake_case naming convention
    def defer_host(self, discord_id):
        """Alias for deferHost using snake_case naming convention."""
        return self.deferHost(discord_id)

    def snoozeHost(self, discord_id):
        """Temporarily removes a user from the hosting rotation."""
        host_logger.info(f"Snoozing host with discord_id={discord_id}")
        try:
            self.connect()
            cursor = self.cursor
            
            # Verify the host exists and is active
            cursor.execute("SELECT username, order_position FROM hosting_rotation WHERE discord_id=? AND active=1", (discord_id,))
            host = cursor.fetchone()
            if not host:
                host_logger.warning(f"Host with discord_id={discord_id} not found or already inactive")
                self.close()
                return "Host not found or already inactive"
                
            username, position = host
            
            # Set user to inactive
            cursor.execute("UPDATE hosting_rotation SET active=0 WHERE discord_id=?", (discord_id,))
            
            # Adjust other positions to maintain continuity
            cursor.execute("UPDATE hosting_rotation SET order_position = order_position - 1 WHERE order_position > ?", (position,))
            
            self.conn.commit()
            host_logger.info(f"Host {username} snoozed successfully")
            self.close()
            return f"Snoozed: {username} removed from the active rotation"
        except Exception as e:
            host_logger.error(f"Error snoozing host: {e}")
            self.conn.rollback()
            self.close()
            raise

    # Alias with snake_case naming convention
    def snooze_host(self, discord_id):
        """Alias for snoozeHost using snake_case naming convention."""
        return self.snoozeHost(discord_id)

    def activateHost(self, discord_id):
        """Re-adds a snoozed user to the hosting rotation."""
        host_logger.info(f"Activating host with discord_id={discord_id}")
        try:
            self.connect()
            cursor = self.cursor
            
            # Verify the host exists and is inactive
            cursor.execute("SELECT username FROM hosting_rotation WHERE discord_id=? AND active=0", (discord_id,))
            host = cursor.fetchone()
            if not host:
                host_logger.warning(f"Host with discord_id={discord_id} not found or already active")
                self.close()
                return "Host not found or already active"
                
            # Get the next available order position
            cursor.execute("SELECT MAX(order_position) FROM hosting_rotation")
            max_pos = cursor.fetchone()[0] or 0
            next_position = max_pos + 1
            
            # Set user to active and add to end of rotation
            cursor.execute("UPDATE hosting_rotation SET active=1, order_position=? WHERE discord_id=?", 
                        (next_position, discord_id))
            
            self.conn.commit()
            host_logger.info(f"Host {host[0]} activated and placed at position {next_position}")
            self.close()
            return f"Activated: {host[0]} added back to rotation at position {next_position}"
        except Exception as e:
            host_logger.error(f"Error activating host: {e}")
            self.conn.rollback()
            self.close()
            raise

    # Alias with snake_case naming convention
    def activate_host(self, discord_id):
        """Alias for activateHost using snake_case naming convention."""
        return self.activateHost(discord_id)

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

    # Alias with snake_case naming convention
    def insert_user_data(self, discord_id, bga_id):
        """Alias for insertUserData using snake_case naming convention."""
        return self.insertUserData(discord_id, bga_id)

    def deleteUserData(self, discord_id):
        """❌ Removes a user from the database."""
        self.connect()
        self.cursor.execute("DELETE FROM user_data WHERE discord_id = ?", (discord_id,))
        self.conn.commit()
        self.close()
        logging.info(f"[DATABASE] User {discord_id} removed.")

    # Alias with snake_case naming convention
    def delete_user_data(self, discord_id):
        """Alias for deleteUserData using snake_case naming convention."""
        return self.deleteUserData(discord_id)

    def getDiscordIdByBgaId(self, bga_id):
        """🔍 Finds a Discord ID from a BGA ID."""
        self.connect()
        self.cursor.execute(
            "SELECT discord_id FROM user_data WHERE bga_id = ?", (bga_id,)
        )
        result = self.cursor.fetchone()
        self.close()
        return result[0] if result else None

    # Alias with snake_case naming convention
    def get_discord_id_by_bga_id(self, bga_id):
        """Alias for getDiscordIdByBgaId using snake_case naming convention."""
        return self.getDiscordIdByBgaId(bga_id)

    def getAllBgaIds(self):
        """🔍 Retrieves all BGA IDs."""
        self.connect()
        self.cursor.execute("SELECT bga_id FROM user_data")
        rows = self.cursor.fetchall()
        self.close()
        return [row[0] for row in rows]

    # Alias with snake_case naming convention
    def get_all_bga_ids(self):
        """Alias for getAllBgaIds using snake_case naming convention."""
        return self.getAllBgaIds()

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

    # Alias with snake_case naming convention
    def insert_game_data(self, id, url, game_name, active_player_id):
        """Alias for insertGameData using snake_case naming convention."""
        return self.insertGameData(id, url, game_name, active_player_id)

    def deleteGameData(self, id):
        """❌ Removes a game entry."""
        self.connect()
        self.cursor.execute("DELETE FROM game_data WHERE id = ?", (id,))
        self.conn.commit()
        self.close()
        logging.info(f"[DATABASE] Game {id} removed.")

    # Alias with snake_case naming convention
    def delete_game_data(self, id):
        """Alias for deleteGameData using snake_case naming convention."""
        return self.deleteGameData(id)

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

    # Alias with snake_case naming convention
    def update_active_player(self, id, active_player_id):
        """Alias for updateActivePlayer using snake_case naming convention."""
        return self.updateActivePlayer(id, active_player_id)

    def getActivePlayer(self, id):
        """🔍 Retrieves the active player ID for a game."""
        self.connect()
        self.cursor.execute("SELECT active_player_id FROM game_data WHERE id = ?", (id,))
        result = self.cursor.fetchone()
        self.close()
        return result[0] if result else None

    # Alias with snake_case naming convention
    def get_active_player(self, id):
        """Alias for getActivePlayer using snake_case naming convention."""
        return self.getActivePlayer(id)

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

    # Alias with snake_case naming convention
    def get_game_by_id(self, game_id):
        """Alias for getGameById using snake_case naming convention."""
        return self.getGameById(game_id)

    def getAllGames(self):
        """🔍 Retrieves all games from the database."""
        self.connect()
        self.cursor.execute("SELECT id, url, game_name, active_player_id FROM game_data")
        games = self.cursor.fetchall()
        self.close()
        return [Game(*game) for game in games]

    # Alias with snake_case naming convention
    def get_all_games(self):
        """Alias for getAllGames using snake_case naming convention."""
        return self.getAllGames()

    def close(self):
        """🔹 Closes the database connection."""
        if self.conn:
            self.conn.close()
            logging.info("[DATABASE] Connection closed.")