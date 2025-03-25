import os
import logging
import sqlite3
from pathlib import Path
from collections import namedtuple
from src.config import Config

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

# Remove global config/database initialization
Game = namedtuple("Game", ["id", "url", "name", "activePlayerId"])

class Database:
    def __init__(self, db_file):
        self.db_file = db_file
        self.conn = None
        self.cursor = None
        # Create parent directory if it doesn't exist
        self.db_file.parent.mkdir(parents=True, exist_ok=True)

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

        # Log the database path for debugging
        logging.info(f"[DATABASE] Initialized at: {self.db_file}")

        # Ensure tables exist on startup
        self.create_tables()

    def connect(self):
        """🔹 Establishes a connection to the SQLite database."""
        logging.info(f"[DATABASE] Connecting to database at: {self.db_file}")
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()

    def create_tables(self):
        """Creates tables if they don't exist."""
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
        self.create_hosting_table()
        self.conn.commit()
        self.close()
        logging.info("[DATABASE] Tables checked/created successfully.")

    # ───────────────────────────────────────────────────────────────
    # 🔹 HOSTING ROTATION FUNCTIONS
    # ───────────────────────────────────────────────────────────────
    def create_hosting_table(self):
        """Creates the hosting rotation table if it doesn't exist."""
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

    def add_host(self, discord_id, username):
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

    def get_next_host(self):
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

    def rotate_hosts(self):
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
            
            # Get the maximum position number from active hosts
            cursor.execute("SELECT MAX(order_position) FROM hosting_rotation WHERE active=1")
            max_pos = cursor.fetchone()[0] or 0
            
            # Move the current host to the back
            cursor.execute("UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ?", 
                        (max_pos + 1, host_id))  # Set to max_pos + 1 temporarily
            
            # Decrement everyone else's position
            cursor.execute("UPDATE hosting_rotation SET order_position = order_position - 1 WHERE discord_id != ? AND active=1", 
                        (host_id,))
            
            # Make the current host's position consistent with the new max
            cursor.execute("SELECT MAX(order_position) FROM hosting_rotation WHERE active=1 AND discord_id != ?", 
                        (host_id,))
            new_max = cursor.fetchone()[0] or 0
            cursor.execute("UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ?", 
                        (new_max + 1, host_id))
            
            # Run a final pass to ensure sequential ordering (no gaps)
            self._resequence_positions()
            
            self.conn.commit()
            host_logger.info(f"Host {host_name} rotated to the end of the queue")
            self.close()
            return f"Rotated: {host_name} moved to the end of the queue"
        except Exception as e:
            host_logger.error(f"Error rotating hosts: {e}")
            self.conn.rollback()
            self.close()
            raise

    def defer_host(self, discord_id):
        """Defers a host (keeps them at their current position)."""
        host_logger.info(f"Deferring host with discord_id={discord_id}")
        try:
            self.connect()
            cursor = self.cursor
            
            # Verify the host exists and is active
            cursor.execute("SELECT username, order_position FROM hosting_rotation WHERE discord_id=? AND active=1", (discord_id,))
            host = cursor.fetchone()
            if not host:
                host_logger.warning(f"Host with discord_id={discord_id} not found or not active")
                self.close()
                return "Host not found or not active"
                
            username, position = host
            
            # No need to change the position of the deferred host
            # Just log that they have been deferred
            cursor.execute("UPDATE hosting_rotation SET last_hosted = DATE('now', '-7 days') WHERE discord_id = ?", 
                        (discord_id,))
            
            self.conn.commit()
            host_logger.info(f"Host {username} deferred successfully (keeping position {position})")
            self.close()
            return f"Deferred: {username} has deferred their turn"
        except Exception as e:
            host_logger.error(f"Error deferring host: {e}")
            self.conn.rollback()
            self.close()
            raise

    def snooze_host(self, discord_id):
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

    def activate_host(self, discord_id):
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
    
    def get_all_hosts(self):
        """Returns all active hosts in their current rotation order."""
        host_logger.info("Fetching all hosts in rotation order")
        try:
            with self:  # This will auto-close the connection
                cursor = self.cursor
                
                # Ensure there are no gaps in positions before fetching
                self._resequence_positions()
                
                cursor.execute("SELECT discord_id, username, order_position FROM hosting_rotation WHERE active=1 ORDER BY order_position ASC")
                hosts = cursor.fetchall()
                
                if hosts:
                    host_logger.info(f"Retrieved {len(hosts)} hosts in rotation order")
                    return [{"discord_id": host[0], "username": host[1], "position": host[2]} for host in hosts]
                else:
                    host_logger.warning("No active hosts found in rotation")
                    return []
        except Exception as e:
            host_logger.error(f"Error fetching all hosts: {e}")
            self.close()
            raise

    def _resequence_positions(self):
        """Helper method to ensure host positions are sequential (1, 2, 3...) with no gaps."""
        try:
            # Get all active hosts ordered by their current position
            self.cursor.execute("SELECT discord_id FROM hosting_rotation WHERE active=1 ORDER BY order_position ASC")
            hosts = self.cursor.fetchall()
            
            # Reassign positions sequentially
            for idx, host in enumerate(hosts, 1):
                self.cursor.execute("UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ?", 
                                (idx, host[0]))
            
            host_logger.info(f"Resequenced positions for {len(hosts)} active hosts")
        except Exception as e:
            host_logger.error(f"Error resequencing positions: {e}")
            raise

    # ───────────────────────────────────────────────────────────────
    # 🔹 USER MANAGEMENT FUNCTIONS 
    # ───────────────────────────────────────────────────────────────
    def insert_user_data(self, discord_id, bga_id):
        """Adds a new user to the database."""
        self.connect()
        try:
            self.cursor.execute(
                "INSERT INTO user_data (discord_id, bga_id) VALUES (?, ?)",
                (discord_id, bga_id),
            )
            self.conn.commit()
            logging.info(f"[DATABASE] User {discord_id} linked to BGA {bga_id}.")
        except sqlite3.IntegrityError:
            logging.warning(f"[DATABASE] User {discord_id} already exists.")
        finally:
            self.close()

    def delete_user_data(self, discord_id):
        """Removes a user from the database."""
        self.connect()
        self.cursor.execute("DELETE FROM user_data WHERE discord_id = ?", (discord_id,))
        self.conn.commit()
        self.close()
        logging.info(f"[DATABASE] User {discord_id} removed.")

    def get_discord_id_by_bga_id(self, bga_id):
        """Finds a Discord ID from a BGA ID."""
        self.connect()
        self.cursor.execute(
            "SELECT discord_id FROM user_data WHERE bga_id = ?", (bga_id,)
        )
        result = self.cursor.fetchone()
        self.close()
        return result[0] if result else None

    def get_all_bga_ids(self):
        """Retrieves all BGA IDs."""
        self.connect()
        self.cursor.execute("SELECT bga_id FROM user_data")
        rows = self.cursor.fetchall()
        self.close()
        return [row[0] for row in rows]

    # ───────────────────────────────────────────────────────────────
    # 🔹 GAME MANAGEMENT FUNCTIONS
    # ───────────────────────────────────────────────────────────────
    def insert_game_data(self, id, url, game_name, active_player_id):
        """Adds a new game entry."""
        self.connect()
        try:
            self.cursor.execute(
                "INSERT INTO game_data (id, url, game_name, active_player_id) VALUES (?, ?, ?, ?)",
                (id, url, game_name, active_player_id),
            )
            self.conn.commit()
            logging.info(f"[DATABASE] Game {id} added ({game_name}).")
        except sqlite3.Error as e:
            logging.error(f"[DATABASE ERROR] {e}")
        finally:
            self.close()

    def delete_game_data(self, id):
        """Removes a game entry."""
        self.connect()
        self.cursor.execute("DELETE FROM game_data WHERE id = ?", (id,))
        self.conn.commit()
        self.close()
        logging.info(f"[DATABASE] Game {id} removed.")

    def update_active_player(self, id, active_player_id):
        """Updates the active player for a game."""
        self.connect()
        self.cursor.execute(
            "UPDATE game_data SET active_player_id = ? WHERE id = ?",
            (active_player_id, id),
        )
        self.conn.commit()
        self.close()
        logging.info(f"[DATABASE] Game {id} updated: Active Player → {active_player_id}.")

    def get_active_player(self, id):
        """Retrieves the active player ID for a game."""
        self.connect()
        self.cursor.execute("SELECT active_player_id FROM game_data WHERE id = ?", (id,))
        result = self.cursor.fetchone()
        self.close()
        return result[0] if result else None

    def get_game_by_id(self, game_id):
        """Retrieves a game by its ID."""
        self.connect()
        self.cursor.execute(
            "SELECT id, url, game_name, active_player_id FROM game_data WHERE id = ?",
            (game_id,),
        )
        result = self.cursor.fetchone()
        self.close()
        return Game(*result) if result else None

    def get_all_games(self):
        """Retrieves all games from the database."""
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