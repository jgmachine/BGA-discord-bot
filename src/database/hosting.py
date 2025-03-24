import logging
from typing import Dict, List, Optional

host_logger = logging.getLogger('hosting_rotation')

class HostDatabase:
    """Host rotation specific database operations."""

    def __init__(self, db_connection):
        self.db = db_connection

    def add_host(self, discord_id: str, username: str) -> bool:
        """Adds a user to the hosting rotation."""
        host_logger.info(f"Adding host: {username}")
        with self.db:
            try:
                # Get next position
                self.db.cursor.execute("SELECT MAX(order_position) FROM hosting_rotation")
                next_position = (self.db.cursor.fetchone()[0] or 0) + 1
                
                self.db.cursor.execute(
                    """INSERT OR IGNORE INTO hosting_rotation 
                       (discord_id, username, order_position) VALUES (?, ?, ?)""",
                    (discord_id, username, next_position)
                )
                return True
            except Exception as e:
                host_logger.error(f"Failed to add host: {e}")
                return False

    def remove_host(self, discord_id: str) -> bool:
        """Removes a host from rotation."""
        with self.db:
            try:
                self.db.cursor.execute("DELETE FROM hosting_rotation WHERE discord_id = ?", (discord_id,))
                return self.db.cursor.rowcount > 0
            except Exception as e:
                host_logger.error(f"Failed to remove host: {e}")
                return False

    def get_next_host(self) -> Optional[Dict[str, str]]:
        """Gets the next host in rotation."""
        with self.db:
            try:
                self.db.cursor.execute(
                    """SELECT discord_id, username 
                       FROM hosting_rotation 
                       WHERE active = 1 
                       ORDER BY order_position ASC LIMIT 1"""
                )
                host = self.db.cursor.fetchone()
                return {"discord_id": host[0], "username": host[1]} if host else None
            except Exception as e:
                host_logger.error(f"Failed to get next host: {e}")
                return None

    def get_all_hosts(self) -> List[Dict[str, any]]:
        """Gets all active hosts in order."""
        with self.db:
            try:
                self.db.cursor.execute(
                    """SELECT discord_id, username, order_position 
                       FROM hosting_rotation 
                       WHERE active = 1 
                       ORDER BY order_position ASC"""
                )
                hosts = self.db.cursor.fetchall()
                return [
                    {"discord_id": h[0], "username": h[1], "position": h[2]} 
                    for h in hosts
                ]
            except Exception as e:
                host_logger.error(f"Failed to get all hosts: {e}")
                return []

    def rotate_hosts(self) -> bool:
        """Rotates the current host to the end."""
        with self.db:
            try:
                # Get current host
                current = self.get_next_host()
                if not current:
                    return False

                # Update positions
                self.db.cursor.execute(
                    """UPDATE hosting_rotation 
                       SET last_hosted = DATE('now'),
                           order_position = (
                               SELECT MAX(order_position) + 1 
                               FROM hosting_rotation 
                               WHERE active = 1
                           )
                       WHERE discord_id = ?""",
                    (current['discord_id'],)
                )

                # Resequence others
                self.db.cursor.execute(
                    """UPDATE hosting_rotation 
                       SET order_position = order_position - 1 
                       WHERE discord_id != ? AND active = 1""",
                    (current['discord_id'],)
                )
                return True
            except Exception as e:
                host_logger.error(f"Failed to rotate hosts: {e}")
                return False
