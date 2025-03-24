import logging
from .core import DatabaseConnection

# Create specific logger for hosting operations
host_logger = logging.getLogger('hosting_rotation')

class HostDatabase(DatabaseConnection):
    """Host rotation specific database operations."""

    def add_host(self, discord_id, username):
        """Adds a user to the hosting rotation."""
        host_logger.info(f"Adding host: {username}")
        with self:
            # Get next position
            self.cursor.execute("SELECT MAX(order_position) FROM hosting_rotation")
            next_position = (self.cursor.fetchone()[0] or 0) + 1
            
            # Insert new host
            self.cursor.execute(
                """INSERT OR IGNORE INTO hosting_rotation 
                   (discord_id, username, order_position) VALUES (?, ?, ?)""",
                (discord_id, username, next_position)
            )
            self.conn.commit()
            return self.cursor.rowcount

    def get_next_host(self):
        """Gets the next host in rotation."""
        with self:
            self.cursor.execute(
                """SELECT discord_id, username 
                   FROM hosting_rotation 
                   WHERE active=1 
                   ORDER BY order_position ASC LIMIT 1"""
            )
            host = self.cursor.fetchone()
            return {"discord_id": host[0], "username": host[1]} if host else None

    # ... other host-specific methods (rotate_hosts, defer_host, etc.) ...
