from pathlib import Path
from .core import DatabaseConnection
from .hosting import HostDatabase
from .bga import BGADatabase, Game

class Database(DatabaseConnection, HostDatabase, BGADatabase):
    """Main database interface combining all functionality."""
    def __init__(self, db_file=Path("/data/database.db")):
        super().__init__(db_file)
