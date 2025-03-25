from .base import BaseDatabase
from .bga_db import BGADatabase
from .hosting_db import HostingDatabase

class Database(BGADatabase, HostingDatabase):
    """Combined database class that inherits all functionality"""
    pass

__all__ = ['Database', 'BaseDatabase', 'BGADatabase', 'HostingDatabase']
