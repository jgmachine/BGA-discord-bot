import logging
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log'
)

class DatabaseConnection:
    """Base class for database operations."""
    
    def __init__(self, db_file):
        self.db_file = db_file
        self.connect()  # Establish connection on init

    def __enter__(self):
        if not self.conn:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit that handles commit/rollback."""
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
            logging.error(f"Database error: {exc_val}")
        # Don't close connection here, keep it open for the bot lifetime

    def connect(self):
        """Establishes database connection."""
        logging.info(f"[DATABASE] Connecting to database at: {self.db_file}")
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()

    def close(self):
        """Closes database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
            logging.info("[DATABASE] Connection closed.")

    def ensure_connected(self):
        """Ensures database is connected."""
        if not self.conn:
            self.connect()

    def create_tables(self):
        """Creates all required tables."""
        with self:
            # Create user_data table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_data (
                    discord_id INTEGER PRIMARY KEY,
                    bga_id TEXT UNIQUE NOT NULL
                )
            """)
            # Create game_data table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS game_data (
                    id INTEGER PRIMARY KEY,
                    url TEXT,
                    game_name TEXT,
                    active_player_id INTEGER
                )
            """)
            # Create hosting_rotation table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS hosting_rotation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id TEXT UNIQUE NOT NULL,
                    username TEXT NOT NULL,
                    order_position INTEGER NOT NULL,
                    last_hosted DATE,
                    active INTEGER DEFAULT 1
                )
            """)
            self.conn.commit()
