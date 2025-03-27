from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import os
from dotenv import load_dotenv

@dataclass
class Config:
    """Central configuration management."""
    discord_token: str
    discord_app_id: Optional[str]
    notify_channel_id: int
    hosting_rotation_channel_id: int
    counting_channel_id: int
    data_dir: Path
    database_path: Path
    target_max: int

    @classmethod
    def load(cls) -> 'Config':
        """Load configuration from environment variables."""
        load_dotenv()

        data_dir = Path("/data")
        
        # Create data directory if it doesn't exist
        data_dir.mkdir(parents=True, exist_ok=True)
        # Ensure proper permissions
        os.system(f"chmod 777 {data_dir}")
        
        database_path = data_dir / "database.db"

        return cls(
            discord_token=os.getenv("DISCORD_TOKEN", ""),
            discord_app_id=os.getenv("DISCORD_APP_ID"),
            notify_channel_id=int(os.getenv("NOTIFY_CHANNEL_ID", "0")),
            hosting_rotation_channel_id=int(os.getenv("HOSTING_ROTATION_CHANNEL_ID", "0")),
            counting_channel_id=int(os.getenv("COUNTING_CHANNEL_ID", "0")),
            data_dir=data_dir,
            database_path=database_path,
            target_max=int(os.getenv('COUNTING_TARGET_MAX', '100'))
        )
