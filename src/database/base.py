import logging
import sqlite3
from pathlib import Path
from contextlib import contextmanager

class BaseDatabase:
    """Base database class with common functionality."""
    
    def __init__(self, db_file: Path):
        self.db_file = db_file
        self.conn = None
        self.cursor = None
        self.db_file.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        try:
            self.connect()
            yield self.cursor
            self.conn.commit()
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise e
        finally:
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
            self.conn = None
            self.cursor = None
            logging.info("[DATABASE] Connection closed.")

    def create_tables(self):
        """Creates all required tables."""
        raise NotImplementedError("Subclasses must implement create_tables()")

    def _execute(self, sql, params=None):
        """Execute SQL and return results before connection close."""
        with self.transaction() as cursor:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            try:
                return cursor.fetchall()
            except sqlite3.OperationalError:
                # No results to fetch (e.g., for INSERT/UPDATE)
                return cursor
