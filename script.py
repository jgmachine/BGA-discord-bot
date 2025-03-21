print("🚀 The script is starting...")

from src import loggingConfig
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from src import messageController
import discord
from discord.ext import commands
from src.database import Database
from src import taskService
import asyncio  # Required for async functions

# Load environment variables
load_dotenv()
loggingConfig.setupLogging()
logging.basicConfig(level=logging.INFO)
logging.info("🚀 Starting the bot script.")
logging.info(f"🔍 Current Working Directory: {os.getcwd()}")

# Set up Discord bot
TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Update this function to reflect the correct extension path
async def load_commands():
    """Loads all commands dynamically from the `src/` folder."""
    try:
        await bot.load_extension("src.hosting_rotation")  # Fixed path
        logging.info("✅ Hosting rotation commands loaded successfully.")
    except Exception as e:
        logging.error(f"❌ Failed to load hosting_rotation extension: {e}")

# Set up database with persistent storage path
DB_DIR = Path("/data")
# Ensure the directory exists with proper permissions
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "database.db"

# Add debug checks for the database path
logging.info(f"🔍 Database directory path: {DB_DIR}")
logging.info(f"🔍 Database file path: {DB_PATH}")
logging.info(f"🔍 Database directory exists: {DB_DIR.exists()}")
logging.info(f"🔍 Database directory is writable: {os.access(DB_DIR, os.W_OK)}")

# Create database instance
database = Database(DB_PATH)
logging.info(f"✅ Database instance created with path: {DB_PATH}")
print(f"✅ DATABASE SETUP COMPLETE - Path: {DB_PATH}")

# Initialize database schema
try:
    # This will connect, create tables, and close the connection
    database.createTables()
    
    # Verify the database file was created
    if DB_PATH.exists():
        logging.info(f"✅ Database file successfully created at {DB_PATH}")
        logging.info(f"✅ Database file size: {DB_PATH.stat().st_size} bytes")
    else:
        logging.error(f"❌ Database file was not created at {DB_PATH}")
except Exception as e:
    logging.error(f"❌ Database initialization failed: {e}")

# Modify the existing on_ready() function to handle commands
@bot.event
async def on_ready():
    logging.info(f"✅ We have logged in as {bot.user}")
    
    # Load bot commands when the bot starts
    await load_commands()
    
    # Start the task service if it's still relevant
    try:
        taskService.processGames.start(bot)
        logging.info("✅ Task service started successfully.")
    except Exception as e:
        logging.error(f"❌ Failed to start task service: {e}")

# Process messages
@bot.event
async def on_message(message):
    # Prevent responding to bot's own messages
    if message.author.bot:
        return
    
    # Process commands from the message
    await bot.process_commands(message)
    
    # Handle custom command processing if needed
    await messageController.handleCommand(bot, message)

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        logging.error("❌ Invalid Discord token. Please check your .env file.")
    except Exception as e:
        logging.error(f"❌ Error starting the bot: {e}")
    finally:
        logging.info("Closing down.")