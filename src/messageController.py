import logging
from pathlib import Path
import sqlite3
from discord.ext import commands
from discord import app_commands
import discord
from . import webscraper
from src.database import Database
from . import utils
import os
from dotenv import load_dotenv

# Use the persistent database path
DB_PATH = Path("/data/database.db")
database = Database(DB_PATH)
load_dotenv()
NOTIFY_CHANNEL_ID = int(os.getenv("NOTIFY_CHANNEL_ID", "0"))

class GameManagementCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="remove_me", description="Remove yourself from the user list")
    async def remove_me(self, interaction: discord.Interaction):
        database.deleteUserData(interaction.user.id)
        await interaction.response.send_message("User deleted!")

    @app_commands.command(name="remove_game", description="Stop monitoring a game")
    @app_commands.describe(game_id="The ID of the game to stop monitoring")
    async def remove_game(self, interaction: discord.Interaction, game_id: str):
        try:
            game = database.getGameById(game_id)
            database.deleteGameData(game_id)
            await interaction.response.send_message(f"Not monitoring {game.name} with id: {game.id}")
        except Exception as e:
            logging.error(f"Error when removing game: {e}")
            await interaction.response.send_message(f"Could not remove game with id: {game_id}")

    @app_commands.command(name="monitor", description="Start monitoring a BGA game")
    @app_commands.describe(url="The URL of the Board Game Arena table")
    async def monitor(self, interaction: discord.Interaction, url: str):
        try:
            game_id = utils.extractGameId(url)
            game_name, active_player_id = await webscraper.getGameInfo(url)

            database.insertGameData(game_id, url, game_name, active_player_id)

            await interaction.response.send_message(
                f"Monitoring {game_name} with id: {game_id} at url: {url}"
            )
            await notifyer(self.bot, active_player_id, game_id)

        except Exception as e:
            logging.error(f"Error when monitoring: {e}")
            await interaction.response.send_message(
                f"Something went wrong when trying to monitor game with url: {url}"
            )

    @app_commands.command(name="add_user", description="Link your Discord account to your BGA ID")
    @app_commands.describe(bga_id="Your Board Game Arena user ID")
    async def add_user(self, interaction: discord.Interaction, bga_id: str):
        try:
            database.insertUserData(discordId=interaction.user.id, bgaId=bga_id)
            await interaction.response.send_message("User added!")
        except sqlite3.IntegrityError as e:
            logging.error(f"Error when adding user: {e}")
            await interaction.response.send_message("Discord user ID already added!")

    @app_commands.command(name="debug_users", description="Show all stored users (debug)")
    async def debug_users(self, interaction: discord.Interaction):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_data")
            rows = cursor.fetchall()
            conn.close()

            if rows:
                await interaction.response.send_message(f"Stored Users: {rows}")
            else:
                await interaction.response.send_message("No users found in the database.")
        except Exception as e:
            await interaction.response.send_message(f"Error accessing database: {e}")
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
async def setup(bot):
    await bot.add_cog(GameManagementCommands(bot))
    await bot.tree.sync()
    logging.info("✅ GameManagementCommands cog has been loaded and commands synced.")