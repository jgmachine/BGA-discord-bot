import logging
from pathlib import Path
from . import webscraper
from src.database import Database
import sqlite3
from . import utils
import os
from dotenv import load_dotenv

# Use the persistent database path
DB_PATH = Path("/data/database.db")
database = Database(DB_PATH)
load_dotenv()
NOTIFY_CHANNEL_ID = int(os.getenv("NOTIFY_CHANNEL_ID", "0"))  # Ensure it's an integer

async def handleCommand(bot, message):
    command = message.content.lower()

    if command.startswith("!hello"):
        await message.channel.send("hello!")

    if command.startswith("!remove_me"):
        database.deleteUserData(message.author.id)
        await message.channel.send("User deleted!")

    if command.startswith("!remove_game"):
        try:
            _, gameId = command.split(" ", 1)
        except Exception:
            await message.channel.send("Provide a game ID to be removed")
            return

        try:
            game = database.getGameById(gameId)
            database.deleteGameData(gameId)

            await message.channel.send(f"Not monitoring {game.name} with id: {game.id}")

        except Exception as e:
            logging.error(f"Error when removing game: {e}")
            await message.channel.send(f"Could not remove game with id: {gameId}")

    elif command.startswith("!monitor"):
        try:
            _, urlParameter = command.split(" ", 1)
        except Exception:
            await message.channel.send("Provide a URL to a board game arena table")
            return

        try:
            gameId = utils.extractGameId(urlParameter)
            gameName, activePlayerId = await webscraper.getGameInfo(urlParameter)

            database.insertGameData(gameId, urlParameter, gameName, activePlayerId)

            await message.channel.send(
                f"Monitoring {gameName} with id: {gameId} at url: {urlParameter}"
            )
            await notifyer(bot, activePlayerId, gameId)

        except Exception as e:
            logging.error(f"Error when monitoring: {e}")
            await message.channel.send(
                f"Something went wrong when trying to monitor game with url: {urlParameter}"
            )

    elif command.startswith("!add_user"):
        try:
            _, bgaId = command.split(" ", 1)
        except Exception:
            await message.channel.send("Provide a BGA user ID")
            return

        discordId = message.author.id

        try:
            database.insertUserData(discordId=discordId, bgaId=bgaId)
            await message.channel.send("User added!")
        except sqlite3.IntegrityError as e:
            logging.error(f"Error when adding user: {e}")
            await message.channel.send("Discord user ID already added!")

    # Updated !debug_users to use the persistent database path
    elif command.startswith("!debug_users"):
        try:
            # Use the same DB_PATH for consistency
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_data")
            rows = cursor.fetchall()
            conn.close()

            if rows:
                await message.channel.send(f"Stored Users: {rows}")
            else:
                await message.channel.send("No users found in the database.")
        except Exception as e:
            await message.channel.send(f"Error accessing database: {e}")
            logging.error(f"Database error: {e}")


async def notifyer(bot, bgaId, gameId):
    logging.info(f"notifyer() triggered for game {gameId} and player {bgaId}")

    discordId = database.getDiscordIdByBgaId(bgaId)
    logging.info(f"Retrieved discordId: {discordId}")

    if discordId:
        mention = f"<@{discordId}>"
        channel = bot.get_channel(NOTIFY_CHANNEL_ID)
        logging.info(f"Channel found: {channel}")

        game = database.getGameById(gameId)
        logging.info(f"Retrieved game: {game}")

        try:
            await channel.send(
                f"It's your turn {mention} in [{game.name}]({game.url})!"
            )
            logging.info("Message sent successfully.")
        except Exception as e:
            logging.error(f"Failed to send message: {e}")