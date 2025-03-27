import logging
from .base import BaseDatabase

# Configure hosting rotation logger
host_logger = logging.getLogger('hosting_rotation')
file_handler = logging.FileHandler('hosting_rotation.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
host_logger.addHandler(file_handler)
host_logger.setLevel(logging.INFO)

class HostingDatabase(BaseDatabase):
    """Hosting-specific database operations."""

    def create_tables(self):
        """Creates hosting rotation tables."""
        # Create host types table
        self._execute('''
            CREATE TABLE IF NOT EXISTS hosting_types (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT
            )
        ''')
        
        # Insert default host types if they don't exist
        self._execute('''
            INSERT OR IGNORE INTO hosting_types (id, name, description) VALUES 
            (1, 'venue', 'Primary venue/house host'),
            (2, 'game', 'Secondary game table host')
        ''')

        # Check if hosting_rotation table exists and get its columns
        results = self._execute("PRAGMA table_info(hosting_rotation)")
        existing_columns = [row[1] for row in results] if results else []
        
        if not existing_columns:
            # Create new table if it doesn't exist
            self._execute('''
                CREATE TABLE hosting_rotation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    order_position INTEGER NOT NULL,
                    last_hosted DATE,
                    active INTEGER DEFAULT 1,
                    host_type_id INTEGER DEFAULT 1,
                    UNIQUE(discord_id, host_type_id),
                    FOREIGN KEY(host_type_id) REFERENCES hosting_types(id)
                )
            ''')
        elif 'host_type_id' not in existing_columns:
            # Add host_type_id column to existing table
            host_logger.info("Adding host_type_id column to existing hosting_rotation table")
            self._execute('''
                ALTER TABLE hosting_rotation 
                ADD COLUMN host_type_id INTEGER DEFAULT 1
            ''')
            # Add unique constraint
            self._execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_discord_host_type 
                ON hosting_rotation(discord_id, host_type_id)
            ''')

        host_logger.info("Hosting rotation tables created/updated successfully")

    def add_host(self, discord_id, username, host_type_id=1):
        """Adds a user to the specified hosting rotation."""
        host_logger.info(f"Adding host: discord_id={discord_id}, username={username}, type={host_type_id}")
        try:
            results = self._execute(
                "SELECT MAX(order_position) FROM hosting_rotation WHERE host_type_id=?",
                (host_type_id,)
            )
            max_pos = results[0][0] if results and results[0][0] is not None else 0
            next_position = max_pos + 1
            
            host_logger.debug(f"Next position calculated as {next_position}")
            
            cursor = self._execute(
                """INSERT OR IGNORE INTO hosting_rotation 
                   (discord_id, username, order_position, host_type_id) 
                   VALUES (?, ?, ?, ?)""",
                (discord_id, username, next_position, host_type_id)
            )
            
            rows_affected = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
            host_logger.info(f"Host added successfully, rows affected: {rows_affected}")
            return rows_affected
        except Exception as e:
            host_logger.error(f"Error adding host: {e}")
            raise

    def get_next_host(self, host_type_id=1):
        """Fetches the next user in the specified hosting rotation."""
        host_logger.info("Fetching next host")
        try:
            cursor = self._execute(
                """SELECT discord_id, username 
                   FROM hosting_rotation 
                   WHERE active=1 AND host_type_id=? 
                   ORDER BY order_position ASC LIMIT 1""",
                (host_type_id,)
            )
            next_host = cursor.fetchone()
            
            if next_host:
                host_logger.info(f"Next host found: {next_host[1]}")
                return {"discord_id": next_host[0], "username": next_host[1]}
            else:
                host_logger.warning("No active hosts found in rotation")
                return None
        except Exception as e:
            host_logger.error(f"Error fetching next host: {e}")
            raise

    def rotate_hosts(self, host_type_id=1):
        """Moves the current host to the back of the queue."""
        host_logger.info("Rotating hosts")
        try:
            cursor = self._execute(
                "SELECT discord_id, username, order_position FROM hosting_rotation WHERE active=1 AND host_type_id=? ORDER BY order_position ASC LIMIT 1",
                (host_type_id,)
            )
            host = cursor.fetchone()
            if not host:
                host_logger.warning("No active hosts found for rotation")
                return "No active hosts found."
                
            host_id, host_name, host_position = host
            host_logger.info(f"Current host: {host_name} (position {host_position})")
            
            self._execute(
                "UPDATE hosting_rotation SET last_hosted = DATE('now') WHERE discord_id = ? AND host_type_id=?",
                (host_id, host_type_id)
            )
            
            cursor = self._execute("SELECT MAX(order_position) FROM hosting_rotation WHERE active=1 AND host_type_id=?",
                                   (host_type_id,))
            max_pos = cursor.fetchone()[0] or 0
            
            self._execute(
                "UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ? AND host_type_id=?",
                (max_pos + 1, host_id, host_type_id)
            )
            
            self._execute(
                "UPDATE hosting_rotation SET order_position = order_position - 1 WHERE discord_id != ? AND active=1 AND host_type_id=?",
                (host_id, host_type_id)
            )
            
            cursor = self._execute(
                "SELECT MAX(order_position) FROM hosting_rotation WHERE active=1 AND discord_id != ? AND host_type_id=?",
                (host_id, host_type_id)
            )
            new_max = cursor.fetchone()[0] or 0
            
            self._execute(
                "UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ? AND host_type_id=?",
                (new_max + 1, host_id, host_type_id)
            )
            
            self._resequence_positions(host_type_id)
            
            host_logger.info(f"Host {host_name} rotated to the end of the queue")
            return f"Rotated: {host_name} moved to the end of the queue"
        except Exception as e:
            host_logger.error(f"Error rotating hosts: {e}")
            raise

    def defer_host(self, discord_id, host_type_id=1):
        """Defers a host (keeps them at their current position)."""
        host_logger.info(f"Deferring host with discord_id={discord_id}")
        try:
            cursor = self._execute(
                "SELECT username, order_position FROM hosting_rotation WHERE discord_id=? AND active=1 AND host_type_id=?", 
                (discord_id, host_type_id)
            )
            host = cursor.fetchone()
            if not host:
                host_logger.warning(f"Host with discord_id={discord_id} not found or not active")
                return "Host not found or not active"
                
            username, position = host
            
            self._execute(
                "UPDATE hosting_rotation SET last_hosted = DATE('now', '-7 days') WHERE discord_id = ? AND host_type_id=?",
                (discord_id, host_type_id)
            )
            
            host_logger.info(f"Host {username} deferred successfully (keeping position {position})")
            return f"Deferred: {username} has deferred their turn"
        except Exception as e:
            host_logger.error(f"Error deferring host: {e}")
            raise

    def snooze_host(self, discord_id, host_type_id=1):
        """Temporarily removes a user from the hosting rotation."""
        host_logger.info(f"Snoozing host with discord_id={discord_id}")
        try:
            cursor = self._execute(
                "SELECT username, order_position FROM hosting_rotation WHERE discord_id=? AND active=1 AND host_type_id=?",
                (discord_id, host_type_id)
            )
            host = cursor.fetchone()
            if not host:
                host_logger.warning(f"Host with discord_id={discord_id} not found or already inactive")
                return "Host not found or already inactive"
                
            username, position = host
            
            self._execute(
                "UPDATE hosting_rotation SET active=0 WHERE discord_id=? AND host_type_id=?",
                (discord_id, host_type_id)
            )
            
            self._execute(
                "UPDATE hosting_rotation SET order_position = order_position - 1 WHERE order_position > ? AND host_type_id=?",
                (position, host_type_id)
            )
            
            host_logger.info(f"Host {username} snoozed successfully")
            return f"Snoozed: {username} removed from the active rotation"
        except Exception as e:
            host_logger.error(f"Error snoozing host: {e}")
            raise

    def activate_host(self, discord_id, host_type_id=1):
        """Re-adds a snoozed user to the hosting rotation."""
        host_logger.info(f"Activating host with discord_id={discord_id}")
        try:
            cursor = self._execute(
                "SELECT username FROM hosting_rotation WHERE discord_id=? AND active=0 AND host_type_id=?",
                (discord_id, host_type_id)
            )
            host = cursor.fetchone()
            if not host:
                host_logger.warning(f"Host with discord_id={discord_id} not found or already active")
                return "Host not found or already active"
                
            cursor = self._execute("SELECT MAX(order_position) FROM hosting_rotation WHERE host_type_id=?",
                                   (host_type_id,))
            max_pos = cursor.fetchone()[0] or 0
            next_position = max_pos + 1
            
            self._execute(
                "UPDATE hosting_rotation SET active=1, order_position=?, host_type_id=? WHERE discord_id=?",
                (next_position, host_type_id, discord_id)
            )
            
            host_logger.info(f"Host {host[0]} activated and placed at position {next_position}")
            return f"Activated: {host[0]} added back to rotation at position {next_position}"
        except Exception as e:
            host_logger.error(f"Error activating host: {e}")
            raise
    
    def get_all_hosts(self, host_type_id=1):
        """Returns all active hosts in their current rotation order."""
        host_logger.info("Fetching all hosts in rotation order")
        try:
            # Ensure there are no gaps in positions before fetching
            self._resequence_positions(host_type_id)
            
            results = self._execute(
                "SELECT discord_id, username, order_position FROM hosting_rotation WHERE active=1 AND host_type_id=? ORDER BY order_position ASC",
                (host_type_id,)
            )
            
            if results:
                host_logger.info(f"Retrieved {len(results)} hosts in rotation order")
                return [{"discord_id": host[0], "username": host[1], "position": host[2]} for host in results]
            else:
                host_logger.warning("No active hosts found in rotation")
                return []
        except Exception as e:
            host_logger.error(f"Error fetching all hosts: {e}")
            raise

    def _resequence_positions(self, host_type_id=1):
        """Helper method to ensure host positions are sequential (1, 2, 3...) with no gaps."""
        try:
            # Get all active hosts ordered by their current position
            results = self._execute(
                "SELECT discord_id FROM hosting_rotation WHERE active=1 AND host_type_id=? ORDER BY order_position ASC",
                (host_type_id,)
            )
            
            # Reassign positions sequentially
            for idx, host in enumerate(results, 1):
                self._execute(
                    "UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ? AND host_type_id=?",
                    (idx, host[0], host_type_id)
                )
            
            host_logger.info(f"Resequenced positions for {len(results)} active hosts")
        except Exception as e:
            host_logger.error(f"Error resequencing positions: {e}")
            raise
