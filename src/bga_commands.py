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

DB_PATH = Path("/data/database.db")
database = Database(DB_PATH)
load_dotenv()
NOTIFY_CHANNEL_ID = int(os.getenv("NOTIFY_CHANNEL_ID", "0"))

class BGACommands(commands.Cog):
    """Commands for managing Board Game Arena integration."""
    
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bga_unlink", description="Unlink your Discord account from BGA")
    async def bga_unlink(self, interaction: discord.Interaction):
        database.delete_user_data(interaction.user.id)
        await interaction.response.send_message("BGA account unlinked!")

    @app_commands.command(name="bga_untrack", description="Stop tracking a BGA game")
    @app_commands.describe(game_id="The ID of the BGA game to stop tracking")
    async def bga_untrack(self, interaction: discord.Interaction, game_id: str):
        try:
            game = database.get_game_by_id(game_id)
            database.delete_game_data(game_id)
            await interaction.response.send_message(f"Stopped tracking {game.name} (ID: {game.id})")
        except Exception as e:
            logging.error(f"Error when removing game: {e}")
            await interaction.response.send_message(f"Could not find BGA game with ID: {game_id}")

    @app_commands.command(name="bga_track", description="Start tracking a BGA game")
    @app_commands.describe(url="The URL of the Board Game Arena table")
    async def bga_track(self, interaction: discord.Interaction, url: str):
        try:
            game_id = utils.extractGameId(url)
            game_name, active_player_id = await webscraper.getGameInfo(url)

            database.insert_game_data(game_id, url, game_name, active_player_id)

            await interaction.response.send_message(
                f"Now tracking BGA game: {game_name} (ID: {game_id})"
            )
            await notify_turn(self.bot, active_player_id, game_id)

        except Exception as e:
            logging.error(f"Error when tracking BGA game: {e}")
            await interaction.response.send_message(
                f"Failed to track BGA game. Please verify the URL is correct: {url}"
            )

    @app_commands.command(name="bga_link", description="Link your Discord account to your BGA ID")
    @app_commands.describe(bga_id="Your Board Game Arena username")
    async def bga_link(self, interaction: discord.Interaction, bga_id: str):
        try:
            database.insert_user_data(discordId=interaction.user.id, bgaId=bga_id)
            await interaction.response.send_message(f"Successfully linked to BGA account: {bga_id}")
        except sqlite3.IntegrityError as e:
            logging.error(f"Error when linking BGA account: {e}")
            await interaction.response.send_message("This Discord account is already linked to a BGA account!")

    @app_commands.command(name="bga_users", description="Show all linked BGA users (debug)")
    async def bga_users(self, interaction: discord.Interaction):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_data")
            rows = cursor.fetchall()
            conn.close()

            if rows:
                await interaction.response.send_message(f"Linked BGA accounts: {rows}")
            else:
                await interaction.response.send_message("No linked BGA accounts found.")
        except Exception as e:
            await interaction.response.send_message(f"Database error: {e}")
            logging.error(f"Database error: {e}")

    @app_commands.command(name="bga_debug", description="Show environment debug info (admin only)")
    @app_commands.default_permissions(administrator=True)
    async def bga_debug(self, interaction: discord.Interaction):
        try:
            env_info = [
                f"🌍 Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'unknown')}",
                f"📂 Data Path: {DB_PATH}",
                f"📁 Files in /data: {list(Path('/data').glob('*'))}"
            ]
            await interaction.response.send_message(
                "Debug Info:\n" + "\n".join(env_info),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Debug error: {e}",
                ephemeral=True
            )

async def notify_turn(bot, bga_id, game_id):
    """Notify a user that it's their turn in a BGA game."""
    logging.info(f"Notifying turn for BGA game {game_id}, player {bga_id}")

    discord_id = database.getDiscordIdByBgaId(bga_id)
    if discord_id:
        mention = f"<@{discord_id}>"
        channel = bot.get_channel(NOTIFY_CHANNEL_ID)
        game = database.getGameById(game_id)

        try:
            await channel.send(
                f"🎲 It's your turn {mention} in [{game.name}]({game.url})!"
            )
            logging.info("Turn notification sent successfully")
        except Exception as e:
            logging.error(f"Failed to send turn notification: {e}")

async def setup(bot):
    await bot.add_cog(BGACommands(bot))
    await bot.tree.sync()
    logging.info("✅ BGA commands loaded and synced")
