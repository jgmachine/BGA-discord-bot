from .base import BaseDatabase

class CountingDatabase(BaseDatabase):
    """Database operations for the counting game."""
    
    def create_tables(self):
        """Creates counting game tables."""
        self._execute('''
            CREATE TABLE IF NOT EXISTS counting_game_state (
                id INTEGER PRIMARY KEY,
                current_count INTEGER NOT NULL,
                target_number INTEGER NOT NULL,
                last_counter INTEGER
            )
        ''')
        
        self._execute('''
            CREATE TABLE IF NOT EXISTS counting_game_scores (
                user_id INTEGER PRIMARY KEY,
                wins INTEGER NOT NULL DEFAULT 0
            )
        ''')

    def get_game_state(self):
        """Get current game state."""
        results = self._execute(
            "SELECT current_count, target_number, last_counter FROM counting_game_state WHERE id = 1"
        )
        return results[0] if results else None

    def save_game_state(self, current_count, target_number, last_counter):
        """Save current game state."""
        self._execute(
            """INSERT OR REPLACE INTO counting_game_state (id, current_count, target_number, last_counter)
            VALUES (1, ?, ?, ?)""",
            (current_count, target_number, last_counter)
        )

    def record_win(self, user_id):
        """Record a win for the user."""
        self._execute(
            """INSERT INTO counting_game_scores (user_id, wins)
            VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET wins = wins + 1""",
            (user_id,)
        )

    def get_leaderboard(self, limit=10):
        """Get top winners."""
        return self._execute(
            """SELECT user_id, wins FROM counting_game_scores 
            ORDER BY wins DESC LIMIT ?""",
            (limit,)
        )
