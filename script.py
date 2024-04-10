from src import loggingConfig
import logging
import os
from dotenv import load_dotenv
from src import messageController
import discord
from discord.ext import commands
from src.database import Database
from src import taskService
import botReference

load_dotenv()
loggingConfig.setupLogging()
TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
botReference.bot = commands.Bot(command_prefix="!", intents=intents)

database = Database("database.db")


@botReference.bot.event
async def on_ready():
    logging.info(f"We have logged in as {botReference.bot.user}")
    database.createTables()
    taskService.processGames.start()


@botReference.bot.event
async def on_message(message):
    if message.author.bot:
        return
    else:
        await messageController.handleCommand(message)


if __name__ == "__main__":
    try:
        botReference.bot.run(TOKEN)
    finally:
        logging.info("Closing down.")
        database.close()
