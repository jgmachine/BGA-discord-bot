import asynciofrom src import loggingConfig




















































        await self.bot.start(self.config.discord_token)                self._setup_bot()        self._setup_database()        """Start the bot application."""    async def start(self) -> None:            logging.error(f"❌ Failed to load extensions: {e}", exc_info=True)        except Exception as e:            logging.info("✅ Extensions loaded and commands synced successfully.")            await self.bot.tree.sync()            # Sync commands globally after loading all extensions                        await self.bot.load_extension("src.counting.counting_game")            # Load counting game last to ensure proper initialization                        await self.bot.load_extension("src.bga_commands")            await self.bot.load_extension("src.hosting_rotation")            # Load BGA and hosting extensions first        try:        """Load bot command extensions."""    async def _load_extensions(self) -> None:            TaskService.processGames.start(self.bot)            await asyncio.sleep(1)  # Give a short delay for extensions to initialize            await self._load_extensions()            # Load extensions and sync commands when bot is ready            logging.info(f"✅ Logged in as {self.bot.user}")        async def on_ready():        @self.bot.event                self.bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())        """Setup bot instance and event handlers."""    def _setup_bot(self):            self.database.create_tables()        with self.database.transaction():        """Setup database and create required tables."""    def _setup_database(self):        self.bot = None        self.database = Database(self.config.database_path)        self.config = Config.load()    def __init__(self):        """Main bot application class."""class BotApp:from src.task_service import TaskServicefrom src.database import Databasefrom src.config import Configimport loggingimport logging
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
            await self.bot.load_extension("src.counting.counting_game")  # Add this line
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