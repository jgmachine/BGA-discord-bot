from .base import BaseDatabase
from .bga_db import BGADatabase
from .hosting_db import HostingDatabase
from .counting_db import CountingDatabase

class Database(BGADatabase, HostingDatabase, CountingDatabase):
    """Combined database class that inherits all functionality"""
    pass

__all__ = ['Database', 'BaseDatabase', 'BGADatabase', 'HostingDatabase', 'CountingDatabase']
