import logging
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

class BaseDatabase:
    """Base database class with common functionality."""
    
    def __init__(self, db_file: Path):
        self.db_file = db_file
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self._transaction_level = 0
        self.db_file.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def transaction(self):
        """Context manager for database transactions with nesting support."""
        try:
            self._start_transaction()
            yield self.cursor
            self._commit_transaction()
        except Exception as e:
            self._rollback_transaction()
            raise e
        finally:
            self._maybe_close_connection()

    def _start_transaction(self):
        """Start a new transaction or join existing one."""
        if not self.conn:
            self.connect()
        self._transaction_level += 1
        
    def _commit_transaction(self):
        """Commit transaction if this is the outermost one."""
        self._transaction_level -= 1
        if self._transaction_level == 0 and self.conn:
            self.conn.commit()
            
    def _rollback_transaction(self):
        """Rollback transaction if this is the outermost one."""
        self._transaction_level = 0
        if self.conn:
            self.conn.rollback()

    def _maybe_close_connection(self):
        """Close connection only if no active transactions."""
        if self._transaction_level == 0:
            self.close()

    def connect(self):
        """Establishes a connection to the SQLite database."""
        if not self.conn:
            logging.info(f"[DATABASE] Connecting to database at: {self.db_file}")
            self.conn = sqlite3.connect(self.db_file)
            self.cursor = self.conn.cursor()
            self._transaction_level = 0

    def close(self):
        """Closes the database connection."""
        if self.conn and self._transaction_level == 0:
            self.conn.close()
            self.conn = None
            self.cursor = None
            logging.info("[DATABASE] Connection closed.")

    def create_tables(self):
        """Creates all required tables."""
        # Let subclasses create their tables
        raise NotImplementedError("Subclasses must implement create_tables()")

    def _execute(self, sql, params=None):
        """Execute SQL and return results."""
        with self.transaction() as cursor:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            try:
                return cursor.fetchall()
            except sqlite3.OperationalError:
                # For statements that don't return results
                return []
