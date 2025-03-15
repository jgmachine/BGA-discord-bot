from src import loggingConfig
import logging
import os
from dotenv import load_dotenv
from src import messageController
import discord
from discord.ext import commands
from src.database import Database
from src import taskService

load_dotenv()
loggingConfig.setupLogging()
TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 🔧 Ensure database path is correct
DATABASE_PATH = "/data/database.db"  # Persistent storage in Railway
database = Database(DATABASE_PATH)

logging.info(f"[DATABASE] Using path: {DATABASE_PATH}")

# ✅ Force table creation on startup
database.createTables()
logging.info("[DATABASE] Tables checked/created successfully.")

@bot.event
async def on_ready():
    logging.info(f"We have logged in as {bot.user}")
    taskService.processGames.start(bot)  # Ensure this is started after tables exist

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
        database.close()
