import logging
from discord.ext import tasks
from pathlib import Path
from . import webscraper
from src.database import Database
from src.config import Config
from . import bga_commands  # Changed from messageController to bga_commands

class BGATaskService:
    def __init__(self):
        self.config = Config.load()  # Load config per instance
        self.database = Database(self.config.database_path)  # Create database per instance

    async def process_game(self, bot, game):
        logging.info(f"Fetching active player for game: {game.name} with id: {game.id}")
        activePlayerId = await webscraper.fetchActivePlayer(game.url)
        previousActivePlayerId = self.database.get_active_player(game.id)
        logging.info(f"Active player id: {activePlayerId}")
        if activePlayerId == None:
            logging.info("No active player id found. Checking if the game has ended")
            if await webscraper.checkIfGameEnded(game.url):
                logging.info("Game results list found, removing game from monitoring")
                self.database.delete_game_data(game.id)
            else:
                logging.info("Game results list not found. Keep monitoring game..")

        elif activePlayerId == previousActivePlayerId:
            logging.info(f"No change of active player with id: {activePlayerId}")

        else:
            logging.info(
                f"New active player in game: {game.id} New player: {activePlayerId} Previous active player: {previousActivePlayerId}"
            )
            self.database.update_active_player(game.id, activePlayerId)
            await bga_commands.notify_turn(bot, activePlayerId, game.id)  # Updated to use bga_commands

    @tasks.loop(minutes=1)
    async def process_games(self, bot):
        games = self.database.get_all_games()
        logging.info(f"Games: {games}")
        for game in games:
            await self.process_game(bot, game)

# Create instance when imported
task_service = BGATaskService()
# Export the process_games method
processGames = task_service.process_games
