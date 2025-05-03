from src import loggingConfig
import logging
from src.config import Config
import discord
from discord.ext import commands
from src.database import Database
from src import taskService
from src.services import service_manager  # Add this import
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
        try:
            self.config.data_dir.mkdir(parents=True, exist_ok=True)
            self.database = Database(self.config.database_path)
            with self.database.transaction():
                # Create tables for all database components
                self.database.create_tables()
                # Explicitly create tables for each component
                self.database.create_bga_tables()
                self.database.create_hosting_tables()
                self.database.create_counting_tables()
            logging.info(f"✅ Database initialized at {self.config.database_path}")
        except Exception as e:
            logging.error(f"❌ Failed to initialize database: {e}")
            raise
        
    def _setup_bot(self) -> None:
        """Initialize Discord bot."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True  # Make sure we can see messages
        self.bot = commands.Bot(
            command_prefix="!",
            intents=intents,
            description="BGA Discord Bot with counting game"
        )
        
    async def _load_extensions(self) -> None:
        """Load bot command extensions."""
        try:
            await self.bot.load_extension("src.hosting_rotation")
            await self.bot.load_extension("src.bga_commands")
            await self.bot.load_extension("src.counting.counting_game")
            await self.bot.load_extension("src.events")  # Updated path
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
            try:
                # Initialize services first
                await service_manager.init()
                
                logging.info(f"✅ Logged in as {self.bot.user}")
                await self._load_extensions()
                taskService.processGames.start(self.bot)
                
                counting_game = self.bot.get_cog('CountingGame')
                if counting_game:
                    await counting_game.announce_game_status()
                    
            except Exception as e:
                logging.error(f"❌ Failed to initialize services: {e}")
        
        try:
            await self.bot.start(self.config.discord_token)
        except Exception as e:
            logging.error(f"❌ Failed to start bot: {e}")
        finally:
            await service_manager.cleanup()

    def run(self) -> None:
        """Run the bot application."""
        asyncio.run(self.start())

if __name__ == "__main__":
    bot = BGABot()
    bot.run()