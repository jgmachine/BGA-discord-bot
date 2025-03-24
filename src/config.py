from pathlib import Path
from dataclasses import dataclass
import os
from dotenv import load_dotenv
import logging

@dataclass
class Config:
    """Central configuration management."""
    discord_token: str
    notify_channel_id: int
    hosting_rotation_channel_id: int
    data_dir: Path
    database_path: Path
    environment: str
    is_production: bool

    @classmethod
    def load(cls) -> 'Config':
        """Load configuration from environment variables."""
        load_dotenv()
        
        # Force check environment (RAILWAY_ENVIRONMENT_NAME is "production" or "dev")
        environment = os.getenv("RAILWAY_ENVIRONMENT_NAME")
        if not environment:
            raise ValueError("RAILWAY_ENVIRONMENT_NAME must be set!")
            
        # Normalize environment names
        environment = "production" if environment == "production" else "development"
            
        # Log critical environment info
        logging.critical(f"🔐 Starting in {environment} environment")
        
        # Use environment-specific database file
        data_dir = Path("/data")
        database_path = data_dir / f"database_{environment}.db"
        
        # Verify mount point
        if not data_dir.exists():
            logging.critical(f"❌ Mount point /data does not exist!")
        else:
            files = list(data_dir.glob("*"))
            logging.critical(f"📁 Current files in /data: {[f.name for f in files]}")

        config = cls(
            discord_token=os.getenv("DISCORD_TOKEN", ""),
            notify_channel_id=int(os.getenv("NOTIFY_CHANNEL_ID", "0")),
            hosting_rotation_channel_id=int(os.getenv("HOSTING_ROTATION_CHANNEL_ID", "0")),
            data_dir=data_dir,
            database_path=database_path,
            environment=environment,
            is_production=environment == "production"
        )
        
        logging.critical(f"💾 Using database: {config.database_path}")
        return config
