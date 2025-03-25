from .base import BaseDatabase
from .bga_db import BGADatabase
from .hosting_db import HostingDatabase
from .counting_db import CountingDatabase

class Database(BGADatabase, HostingDatabase, CountingDatabase):
    """Combined database class that inherits all functionality"""
    
    def create_tables(self):
        """Creates all required tables."""
        self.create_bga_tables()
        self.create_hosting_tables() 
        self.create_counting_tables()

    def create_bga_tables(self):
        """Create BGA-specific tables."""
        BGADatabase.create_tables(self)

    def create_hosting_tables(self):
        """Create hosting-specific tables."""
        HostingDatabase.create_tables(self)

    def create_counting_tables(self):
        """Create counting-specific tables."""
        CountingDatabase.create_tables(self)

__all__ = ['Database', 'BaseDatabase', 'BGADatabase', 'HostingDatabase', 'CountingDatabase']
