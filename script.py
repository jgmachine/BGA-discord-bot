from src import loggingConfig
import logging
from src.config import Config
import discord
from discord.ext import commands
from src.database import Database
from src import taskService
import asyncio
from pathlib import Path
from typing import Optional

class BGABot:
    def __init__(self):
        self.config: Config = Config.load()
        self.bot: Optional[commands.Bot] = None
        self.database: Optional[Database] = None
        self._setup_logging()
        
    def _setup_logging(self) -> None:
        """Initialize logging configuration."""
        loggingConfig.setupLogging()
        logging.info("🚀 Starting the BGA Discord bot.")
        
    def _setup_database(self) -> None:
        """Initialize database connection."""
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        self.database = Database(self.config.database_path)
        self.database.createTables()
        logging.info(f"✅ Database initialized at {self.config.database_path}")
        
    def _setup_bot(self) -> None:
        """Initialize Discord bot."""
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
    async def _load_extensions(self) -> None:
        """Load bot command extensions."""
        try:
            await self.bot.load_extension("src.hosting_rotation")
            await self.bot.load_extension("src.messageController")  # Add this line
            logging.info("✅ Extensions loaded successfully.")
        except Exception as e:
            logging.error(f"❌ Failed to load extensions: {e}")
            
    async def start(self) -> None:
        """Start the bot application."""
        self._setup_database()
        self._setup_bot()
        
        @self.bot.event
        async def on_ready():
            logging.info(f"✅ Logged in as {self.bot.user}")
            await self._load_extensions()
            taskService.processGames.start(self.bot)
            
        try:
            await self.bot.start(self.config.discord_token)
        except Exception as e:
            logging.error(f"❌ Failed to start bot: {e}")
            
    def run(self) -> None:
        """Run the bot application."""
        asyncio.run(self.start())

if __name__ == "__main__":
    bot = BGABot()
    bot.run()