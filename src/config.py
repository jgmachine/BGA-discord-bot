from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import os
from dotenv import load_dotenv

@dataclass
class Config:
    """Central configuration management."""
    discord_token: str
    notify_channel_id: int
    hosting_rotation_channel_id: int
    data_dir: Path
    database_path: Path
    is_production: bool

    @classmethod
    def load(cls) -> 'Config':
        """Load configuration from environment variables."""
        load_dotenv()
        
        is_production = os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production"
        data_dir = Path("/data-prod" if is_production else "/data-dev")
        database_path = data_dir / "database.db"

        return cls(
            discord_token=os.getenv("DISCORD_TOKEN", ""),
            notify_channel_id=int(os.getenv("NOTIFY_CHANNEL_ID", "0")),
            hosting_rotation_channel_id=int(os.getenv("HOSTING_ROTATION_CHANNEL_ID", "0")),
            data_dir=data_dir,
            database_path=database_path,
            is_production=is_production
        )
