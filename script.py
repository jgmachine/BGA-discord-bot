from src import loggingConfig
import logging
import os
from dotenv import load_dotenv
from src import messageController
import discord
from discord.ext import commands
from src.database import Database
from src import taskService

# Load environment variables
load_dotenv()
loggingConfig.setupLogging()

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize Database (tables are automatically created in the constructor)
database = Database()

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
