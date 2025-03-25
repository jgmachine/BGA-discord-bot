import logging
import sqlite3
from pathlib import Path

class BaseDatabase:
    """Base database class with common functionality."""
    
    def __init__(self, db_file: Path):
        self.db_file = db_file
        self.conn = None
        self.cursor = None
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def connect(self):
        """Establishes a connection to the SQLite database."""
        logging.info(f"[DATABASE] Connecting to database at: {self.db_file}")
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            logging.info("[DATABASE] Connection closed.")

    def create_tables(self):
        """Creates all required tables."""
        raise NotImplementedError("Subclasses must implement create_tables()")

    def _execute(self, sql, params=None):
        """Execute SQL with error handling and connection management."""
        try:
            self.connect()
            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)
            self.conn.commit()
            return self.cursor
        except Exception as e:
            self.conn.rollback()
            raise e
        finally:
            self.close()
