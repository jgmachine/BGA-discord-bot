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

        # Debug: Write environment marker file
        env_file = self.config.data_dir / "environment.txt"
        env_file.write_text(self.config.environment)
        
        # Debug: Log environment setup
        logging.info("🔧 Environment Setup:")
        logging.info(f"  • Environment: {self.config.environment}")
        logging.info(f"  • Production Mode: {self.config.is_production}")
        logging.info(f"  • Data Directory: {self.config.data_dir}")
        logging.info(f"  • Database Path: {self.config.database_path}")

        self.database = Database(self.config.database_path)
        self.database.create_tables()
        
        # Verify database setup
        try:
            self.database._connection.cursor.execute("SELECT 1")
            logging.info("✅ Database connection verified")
        except Exception as e:
            logging.error(f"❌ Database connection failed: {e}")
            raise
        
    def _setup_bot(self) -> None:
        """Initialize Discord bot."""
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
    async def _load_extensions(self) -> None:
        """Load bot command extensions."""
        try:
            await self.bot.load_extension("src.hosting_rotation")
            await self.bot.load_extension("src.bga_commands")
            # Sync commands globally after loading extensions
            await self.bot.tree.sync()
            logging.info("✅ Extensions loaded and commands synced successfully.")
        except Exception as e:
            logging.error(f"❌ Failed to load extensions: {e}")
            
    async def start(self) -> None:
        """Start the bot application."""
        self._setup_database()
        self._setup_bot()
        
        @self.bot.event
        async def on_ready():
            logging.info(f"✅ Logged in as {self.bot.user}")
            # Load extensions and sync commands when bot is ready
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