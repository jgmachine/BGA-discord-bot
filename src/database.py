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

from pathlib import Path
from .database.core import DatabaseConnection 
from .database.hosting import HostDatabase
from .database.bga import BGADatabase, Game

# 🔹 Ensure the /data directory exists for persistent storage
DB_DIR = Path("/data")
DB_DIR.mkdir(parents=True, exist_ok=True)  # Ensures the directory exists
DB_PATH = DB_DIR / "database.db"

class Database(DatabaseConnection, HostDatabase, BGADatabase):
    """Main database interface combining all functionality."""
    def __init__(self, db_file=DB_PATH):
        super().__init__(db_file)