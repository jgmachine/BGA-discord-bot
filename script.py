from src import loggingConfig
import logging
import os
from dotenv import load_dotenv
from src import messageController
import discord
from discord.ext import commands
from src.database import Database
from src import taskService

print("🚀 The script is starting...")


# Load environment variables
load_dotenv()
loggingConfig.setupLogging()
logging.basicConfig(level=logging.INFO)

logging.info("🚀 Starting the bot script.")
logging.info(f"🔍 Current Working Directory: {os.getcwd()}")

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

DB_PATH = "/data/database.db"
database = Database(DB_PATH)  

if database:
    logging.info(f"✅ Database instance successfully created at {DB_PATH}!")
else:
    logging.error("❌ Database instance creation failed!")

# Call `connect` to ensure the database file exists
database.connect()

# Force table creation immediately to verify it works
try:
    database.createTables()
    logging.info("✅ Tables checked/created successfully.")
except Exception as e:
    logging.error(f"❌ Table creation failed: {e}")

@bot.event
async def on_ready():
    logging.info(f"We have logged in as {bot.user}")
    taskService.processGames.start(bot)  # Keep this if still relevant

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    else:
        await messageController.handleCommand(bot, message)

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    finally:
        logging.info("Closing down.")
