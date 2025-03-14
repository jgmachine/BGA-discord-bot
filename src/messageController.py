import logging
from . import webscraper
from src.database import Database
import sqlite3
from . import utils
import os
from dotenv import load_dotenv

database = Database("database.db")
load_dotenv()
NOTIFY_CHANNEL_ID = os.getenv("NOTIFY_CHANNEL_ID")


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
            await message.channel.send("Provide a game id to be removed")
            return

        try:
            game = database.getGameById(gameId)
            database.deleteGameData(gameId)

            await message.channel.send(f"Not monitoring {game.name} with id: {game.id}")

        except Exception as e:
            logging.error(f"Error when remoing game: {e}")
            await message.channel.send(f"Could not remove game with id: {gameId}")

    #!Listen_to command handling:
    elif command.startswith("!monitor"):
        # Get url from command
        try:
            _, urlParameter = command.split(" ", 1)
        except Exception:
            await message.channel.send("Provide a URL to a board game arena table")
            return

        try:
            # Get game id from game url
            gameId = utils.extractGameId(urlParameter)

            # Get game name and current active player
            gameName, activePlayerId = await webscraper.getGameInfo(urlParameter)

            database.insertGameData(gameId, urlParameter, gameName, activePlayerId)

            await message.channel.send(
                f"Monitoring to {gameName} with id: {gameId} at url: {urlParameter}"
            )
            await notifyer(bot, activePlayerId, gameId)

        except Exception as e:
            logging.error(f"Error when monitoring: {e}")
            await message.channel.send(
                f"Something went wrong when trying to monitoring to game with url: {urlParameter}"
            )

    #!Add_user command handling
    elif command.startswith("!add_user"):
        try:
            _, bgaId = command.split(" ", 1)
        except Exception as e:
            await message.channel.send("Provide a BGA user ID")
            return

        discordId = message.author.id

        try:
            database.insertUserData(discordId=discordId, bgaId=bgaId)
            await message.channel.send("user added!")
        except sqlite3.IntegrityError as e:
            logging.error(f"Error when adding user: {e}")
            await message.channel.send("Discord user ID already added!")


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
                f"It's your turn {mention} in {game.name}! [Link]({game.url})"
            )
            logging.info("Message sent successfully.")
        except Exception as e:
            logging.error(f"Failed to send message: {e}")


async def on_message(message):
    if message.author == bot.user:
        return

    command = message.content.lower()

    if command.startswith("!debug_users"):
        try:
            conn = sqlite3.connect("database.db")
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
