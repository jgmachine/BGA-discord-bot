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
        """Creates or updates hosting rotation tables."""
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
                    venue_position INTEGER,
                    game_position INTEGER,
                    last_venue_hosted DATE,
                    last_game_hosted DATE,
                    venue_active INTEGER DEFAULT 0,
                    game_active INTEGER DEFAULT 0
                )
            ''')
            host_logger.info("Created new hosting_rotation table")
        else:
            # Add any missing columns
            needed_columns = {
                'venue_position': 'INTEGER',
                'game_position': 'INTEGER',
                'last_venue_hosted': 'DATE',
                'last_game_hosted': 'DATE',
                'venue_active': 'INTEGER DEFAULT 0',
                'game_active': 'INTEGER DEFAULT 0'
            }
            
            for col_name, col_type in needed_columns.items():
                if col_name not in existing_columns:
                    self._execute(f'ALTER TABLE hosting_rotation ADD COLUMN {col_name} {col_type}')
                    host_logger.info(f"Added column {col_name} to hosting_rotation table")
            
            # If we're migrating from the old schema, convert existing data
            if 'order_position' in existing_columns:
                host_logger.info("Migrating from old schema...")
                # Copy order_position to venue_position and set venue_active for existing hosts
                self._execute('''
                    UPDATE hosting_rotation 
                    SET venue_position = order_position,
                        venue_active = active
                    WHERE order_position IS NOT NULL
                ''')
                
                # Consider dropping old columns if needed
                # self._execute('ALTER TABLE hosting_rotation DROP COLUMN order_position')
                # self._execute('ALTER TABLE hosting_rotation DROP COLUMN active')
        
        host_logger.info("Hosting rotation tables checked/updated successfully")

    def add_host(self, discord_id, username, host_type_id=1):
        """Adds a user to the specified hosting rotation."""
        try:
            # First check if user exists
            results = self._execute(
                "SELECT id FROM hosting_rotation WHERE discord_id=?",
                (discord_id,)
            )
            
            if not results:
                # New user - insert them
                self._execute(
                    """INSERT INTO hosting_rotation 
                       (discord_id, username, venue_position, game_position, 
                        venue_active, game_active) 
                       VALUES (?, ?, NULL, NULL, 0, 0)""",
                    (discord_id, username)
                )
            
            # Get max position for the appropriate rotation
            position_field = "venue_position" if host_type_id == 1 else "game_position"
            active_field = "venue_active" if host_type_id == 1 else "game_active"
            
            results = self._execute(
                f"SELECT MAX({position_field}) FROM hosting_rotation WHERE {active_field}=1"
            )
            max_pos = results[0][0] if results and results[0][0] is not None else 0
            next_position = max_pos + 1
            
            # Update the user's position and active status for the specified rotation
            self._execute(
                f"""UPDATE hosting_rotation 
                    SET {position_field}=?, {active_field}=1 
                    WHERE discord_id=?""",
                (next_position, discord_id)
            )
            
            host_logger.info(f"Host added to {'venue' if host_type_id == 1 else 'game'} rotation")
            return True
            
        except Exception as e:
            host_logger.error(f"Error adding host: {e}")
            raise

    def get_next_host(self, host_type_id=1):
        """Fetches the next user in the specified hosting rotation."""
        position_field = "venue_position" if host_type_id == 1 else "game_position"
        active_field = "venue_active" if host_type_id == 1 else "game_active"
        
        try:
            results = self._execute(
                f"""SELECT discord_id, username 
                    FROM hosting_rotation 
                    WHERE {active_field}=1 
                    ORDER BY {position_field} ASC LIMIT 1"""
            )
            
            if results:
                return {"discord_id": results[0][0], "username": results[0][1]}
            return None
            
        except Exception as e:
            host_logger.error(f"Error getting next host: {e}")
            raise

    def rotate_hosts(self, host_type_id=1):
        """Moves the current host to the back of the queue."""
        position_field = "venue_position" if host_type_id == 1 else "game_position"
        active_field = "venue_active" if host_type_id == 1 else "game_active"
        last_hosted_field = "last_venue_hosted" if host_type_id == 1 else "last_game_hosted"
        
        host_logger.info("Rotating hosts")
        try:
            results = self._execute(
                f"SELECT discord_id, username, {position_field} FROM hosting_rotation WHERE {active_field}=1 ORDER BY {position_field} ASC LIMIT 1"
            )
            
            if not results or len(results) == 0:
                host_logger.warning("No active hosts found for rotation")
                return "No active hosts found."
                
            host_id, host_name, host_position = results[0]
            host_logger.info(f"Current host: {host_name} (position {host_position})")
            
            # Update last hosted date
            self._execute(
                f"UPDATE hosting_rotation SET {last_hosted_field} = DATE('now') WHERE discord_id = ?",
                (host_id,)
            )
            
            # Get max position
            results = self._execute(f"SELECT MAX({position_field}) FROM hosting_rotation WHERE {active_field}=1")
            max_pos = results[0][0] if results and results[0][0] is not None else 0
            
            # Move current host to end
            self._execute(
                f"UPDATE hosting_rotation SET {position_field} = ? WHERE discord_id = ?",
                (max_pos + 1, host_id)
            )
            
            # Move everyone else up
            self._execute(
                f"UPDATE hosting_rotation SET {position_field} = {position_field} - 1 WHERE discord_id != ? AND {active_field}=1",
                (host_id,)
            )
            
            # Resequence to ensure no gaps
            self._resequence_positions(host_type_id)
            
            host_logger.info(f"Host {host_name} rotated to the end of the queue")
            return f"Rotated: {host_name} moved to the end of the queue"
            
        except Exception as e:
            host_logger.error(f"Error rotating hosts: {e}")
            raise

    def defer_host(self, discord_id, host_type_id=1):
        """Defers a host (keeps them at their current position)."""
        position_field = "venue_position" if host_type_id == 1 else "game_position"
        last_hosted_field = "last_venue_hosted" if host_type_id == 1 else "last_game_hosted"
        active_field = "venue_active" if host_type_id == 1 else "game_active"
        
        host_logger.info(f"Deferring host with discord_id={discord_id}")
        try:
            cursor = self._execute(
                f"SELECT username, {position_field} FROM hosting_rotation WHERE discord_id=? AND {active_field}=1", 
                (discord_id,)
            )
            host = cursor.fetchone()
            if not host:
                host_logger.warning(f"Host with discord_id={discord_id} not found or not active")
                return "Host not found or not active"
                
            username, position = host
            
            self._execute(
                f"UPDATE hosting_rotation SET {last_hosted_field} = DATE('now', '-7 days') WHERE discord_id = ?",
                (discord_id,)
            )
            
            host_logger.info(f"Host {username} deferred successfully (keeping position {position})")
            return f"Deferred: {username} has deferred their turn"
        except Exception as e:
            host_logger.error(f"Error deferring host: {e}")
            raise

    def snooze_host(self, discord_id, host_type_id=1):
        """Temporarily removes a user from the hosting rotation."""
        position_field = "venue_position" if host_type_id == 1 else "game_position"
        active_field = "venue_active" if host_type_id == 1 else "game_active"
        
        host_logger.info(f"Snoozing host with discord_id={discord_id}")
        try:
            cursor = self._execute(
                f"SELECT username, {position_field} FROM hosting_rotation WHERE discord_id=? AND {active_field}=1",
                (discord_id,)
            )
            host = cursor.fetchone()
            if not host:
                host_logger.warning(f"Host with discord_id={discord_id} not found or already inactive")
                return "Host not found or already inactive"
                
            username, position = host
            
            self._execute(
                f"UPDATE hosting_rotation SET {active_field}=0 WHERE discord_id=?",
                (discord_id,)
            )
            
            self._execute(
                f"UPDATE hosting_rotation SET {position_field} = {position_field} - 1 WHERE {position_field} > ?",
                (position,)
            )
            
            host_logger.info(f"Host {username} snoozed successfully")
            return f"Snoozed: {username} removed from the active rotation"
        except Exception as e:
            host_logger.error(f"Error snoozing host: {e}")
            raise

    def activate_host(self, discord_id, host_type_id=1):
        """Re-adds a snoozed user to the hosting rotation."""
        position_field = "venue_position" if host_type_id == 1 else "game_position"
        active_field = "venue_active" if host_type_id == 1 else "game_active"
        
        host_logger.info(f"Activating host with discord_id={discord_id}")
        try:
            cursor = self._execute(
                f"SELECT username FROM hosting_rotation WHERE discord_id=? AND {active_field}=0",
                (discord_id,)
            )
            host = cursor.fetchone()
            if not host:
                host_logger.warning(f"Host with discord_id={discord_id} not found or already active")
                return "Host not found or already active"
                
            cursor = self._execute(f"SELECT MAX({position_field}) FROM hosting_rotation")
            max_pos = cursor.fetchone()[0] or 0
            next_position = max_pos + 1
            
            self._execute(
                f"UPDATE hosting_rotation SET {active_field}=1, {position_field}=? WHERE discord_id=?",
                (next_position, discord_id)
            )
            
            host_logger.info(f"Host {host[0]} activated and placed at position {next_position}")
            return f"Activated: {host[0]} added back to rotation at position {next_position}"
        except Exception as e:
            host_logger.error(f"Error activating host: {e}")
            raise
    
    def get_all_hosts(self, host_type_id=1):
        """Returns all active hosts in their current rotation order."""
        position_field = "venue_position" if host_type_id == 1 else "game_position"
        active_field = "venue_active" if host_type_id == 1 else "game_active"
        
        host_logger.info("Fetching all hosts in rotation order")
        try:
            # Ensure there are no gaps in positions before fetching
            self._resequence_positions(host_type_id)
            
            results = self._execute(
                f"SELECT discord_id, username, {position_field} FROM hosting_rotation WHERE {active_field}=1 ORDER BY {position_field} ASC",
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
        position_field = "venue_position" if host_type_id == 1 else "game_position"
        active_field = "venue_active" if host_type_id == 1 else "game_active"
        
        try:
            # Get all active hosts ordered by their current position
            results = self._execute(
                f"SELECT discord_id FROM hosting_rotation WHERE {active_field}=1 ORDER BY {position_field} ASC",
            )
            
            # Reassign positions sequentially
            for idx, host in enumerate(results, 1):
                self._execute(
                    f"UPDATE hosting_rotation SET {position_field} = ? WHERE discord_id = ?",
                    (idx, host[0])
                )
            
            host_logger.info(f"Resequenced positions for {len(results)} active hosts")
        except Exception as e:
            host_logger.error(f"Error resequencing positions: {e}")
            raise

    def debug_schema(self):
        """Debug method to print current table schema."""
        try:
            results = self._execute("PRAGMA table_info(hosting_rotation)")
            columns = [(row[1], row[2]) for row in results]
            host_logger.info(f"Current hosting_rotation schema: {columns}")
        except Exception as e:
            host_logger.error(f"Error getting schema: {e}")
