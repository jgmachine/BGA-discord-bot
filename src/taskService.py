import logging
from discord.ext import tasks
from pathlib import Path
from . import webscraper
from src.database import Database
from src.config import Config
from . import bga_commands  # Changed from messageController to bga_commands

config = Config.load()
database = Database(config.database_path)


# Fetching active player id for a game entity
# If no active player id was found:
#   1. Do new request to check for game results (game has ended)
#   2. If game didn't end, keep monitoring the game until active player is found or game ended.
#
# If the fetched player id is the same as last time, do nothing
#
# If the fetched player id is new, update game entity with new active player id and notify discord user
async def processGame(bot, game):
    logging.info(f"Fetching active player for game: {game.name} with id: {game.id}")
    activePlayerId = await webscraper.fetchActivePlayer(game.url)
    previousActivePlayerId = database.getActivePlayer(game.id)
    logging.info(f"Active player id: {activePlayerId}")
    if activePlayerId == None:
        logging.info("No active player id found. Checking if the game has ended")
        if await webscraper.checkIfGameEnded(game.url):
            logging.info("Game results list found, removing game from monitoring")
            database.deleteGameData(game.id)
        else:
            logging.info("Game results list not found. Keep monitoring game..")

    elif activePlayerId == previousActivePlayerId:
        logging.info(f"No change of active player with id: {activePlayerId}")

    else:
        logging.info(
            f"New active player in game: {game.id} New player: {activePlayerId} Previous active player: {previousActivePlayerId}"
        )
        database.updateActivePlayer(game.id, activePlayerId)
        await bga_commands.notify_turn(bot, activePlayerId, game.id)  # Updated to use bga_commands


# Task for fetching active player ids and update database if active player changed
@tasks.loop(minutes=1)
async def processGames(bot):
    games = database.getAllGames()
    logging.info(f"Games: {games}")

    for game in games:
        await processGame(bot, game)
