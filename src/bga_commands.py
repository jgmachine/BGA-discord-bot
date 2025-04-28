import logging
import sqlite3
from discord.ext import commands
from discord import app_commands
import discord
from . import webscraper
from src.database import Database
from . import utils
from src.config import Config

config = Config.load()
database = Database(config.database_path)
NOTIFY_CHANNEL_ID = config.notify_channel_id

class BGACommands(commands.Cog):
    """Commands for managing Board Game Arena integration."""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.load()  # Load config per instance
        self.database = Database(self.config.database_path)  # Create database per instance
        self.notify_channel_id = self.config.notify_channel_id

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
            # Use instance database instead of global
            self.database.insert_user_data(interaction.user.id, bga_id)
            await interaction.response.send_message(f"Successfully linked to BGA account: {bga_id}")
            logging.info(f"User {interaction.user.id} linked to BGA account {bga_id}")
        except sqlite3.IntegrityError:
            await interaction.response.send_message("This Discord account or BGA ID is already linked!", ephemeral=True)
            logging.warning(f"Failed to link user {interaction.user.id} - already exists")
        except Exception as e:
            await interaction.response.send_message("An error occurred while linking your account. Please try again.", ephemeral=True)
            logging.error(f"Error linking BGA account: {e}")

    @app_commands.command(name="bga_users", description="Show all linked BGA users (debug)")
    async def bga_users(self, interaction: discord.Interaction):
        try:
            users = database.get_all_bga_ids()
            if users:
                await interaction.response.send_message(f"Linked BGA accounts: {users}")
            else:
                await interaction.response.send_message("No linked BGA accounts found.")
        except Exception as e:
            await interaction.response.send_message(f"Database error: {e}")
            logging.error(f"Database error: {e}")

    @app_commands.command(name="bga_games", description="Show all tracked BGA games")
    async def bga_games(self, interaction: discord.Interaction):
        """Shows all games currently being tracked"""
        try:
            games = database.get_all_games()
            if games:
                embed = discord.Embed(
                    title="🎲 Tracked BGA Games",
                    color=discord.Color.blue()
                )
                for game in games:
                    embed.add_field(
                        name=f"{game.name} (ID: {game.id})",
                        value=f"[Game Link]({game.url})",
                        inline=False
                    )
                await interaction.response.send_message(embed=embed)
                logging.info(f"✅ Displayed {len(games)} tracked games")
            else:
                await interaction.response.send_message("No games currently being tracked.")
        except Exception as e:
            await interaction.response.send_message(f"Database error: {e}")
            logging.error(f"Database error: {e}")

    @app_commands.command(name="bga_settings", description="Show your current BGA settings")
    async def bga_settings(self, interaction: discord.Interaction):
        """Show current user settings"""
        try:
            settings = self.database.get_user_settings(interaction.user.id)
            if not settings:
                await interaction.response.send_message(
                    "You don't have any BGA settings configured yet. Use `/bga_link` to get started!", 
                    ephemeral=True
                )
                return

            # Get notification status
            notification_status = "Disabled"
            if settings.get('channel_enabled') and settings.get('dm_enabled'):
                notification_status = "Channel and DM"
            elif settings.get('channel_enabled'):
                notification_status = "Channel only"
            elif settings.get('dm_enabled'):
                notification_status = "DM only"

            embed = discord.Embed(
                title="🎲 Your BGA Settings",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="BGA Username", 
                value=settings['bga_id'], 
                inline=False
            )
            embed.add_field(
                name="Notifications", 
                value=notification_status,
                inline=False
            )
            embed.set_footer(text="Use /bga_notifications to update your notification preferences")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                "An error occurred while fetching your settings.", 
                ephemeral=True
            )
            logging.error(f"Error fetching user settings: {e}")

    @app_commands.command(name="bga_notifications", description="Set your notification preferences for BGA turns")
    @app_commands.describe(setting="Choose how you want to receive notifications")
    @app_commands.choices(setting=[
        app_commands.Choice(name="Channel only", value="channel"),
        app_commands.Choice(name="DM only", value="dm"),
        app_commands.Choice(name="Both Channel and DM", value="both"),
        app_commands.Choice(name="Disabled", value="none")
    ])
    async def bga_notifications(self, interaction: discord.Interaction, setting: app_commands.Choice[str]):
        """Set notification preferences for BGA turns"""
        try:
            settings = self.database.get_user_settings(interaction.user.id)
            if not settings:
                await interaction.response.send_message(
                    "You need to link your BGA account first using `/bga_link`!",
                    ephemeral=True
                )
                return

            # Convert setting to boolean flags
            channel = setting.value in ("channel", "both")
            dm = setting.value in ("dm", "both")
            
            self.database.set_notification_preferences(interaction.user.id, channel, dm)
            
            embed = discord.Embed(
                title="🔔 Notification Settings Updated",
                description=f"Notifications set to: {setting.name}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logging.info(f"User {interaction.user.id} updated notification settings to {setting.value}")

        except Exception as e:
            await interaction.response.send_message(
                "An error occurred while updating your preferences.", 
                ephemeral=True
            )
            logging.error(f"Error updating notification preferences: {e}")

async def notify_turn(bot, bga_id, game_id):
    """Notify a user that it's their turn in a BGA game."""
    logging.info(f"Notifying turn for BGA game {game_id}, player {bga_id}")

    discord_id = database.get_discord_id_by_bga_id(bga_id)
    if discord_id:
        discord_id = int(discord_id)
        user = await bot.fetch_user(discord_id)
        if not user:
            logging.error(f"Could not fetch user with ID {discord_id}")
            return

        game = database.get_game_by_id(game_id)
        prefs = database.get_notification_preferences(discord_id)
        
        if not prefs:
            logging.error(f"No notification preferences found for user {discord_id}")
            return

        # Send channel notification if enabled
        if prefs['channel_enabled']:
            try:
                channel = bot.get_channel(NOTIFY_CHANNEL_ID)
                mention = f"<@{discord_id}>"
                await channel.send(
                    f"🎲 It's your turn {mention} in [{game.name}]({game.url})!"
                )
                logging.info("Turn notification sent to channel successfully")
            except Exception as e:
                logging.error(f"Failed to send channel notification: {e}")

        # Send DM if enabled
        if prefs['dm_enabled']:
            logging.info(f"Attempting to send DM to user {discord_id}")
            try:
                dm_channel = await user.create_dm()
                await dm_channel.send(
                    f"🎲 It's your turn in [{game.name}]({game.url})!"
                )
                logging.info("Turn notification sent via DM successfully")
            except discord.Forbidden:
                logging.error(f"Could not send DM - user {discord_id} has DMs disabled")
            except Exception as e:
                logging.error(f"Failed to send DM notification: {e}")

async def setup(bot):
    await bot.add_cog(BGACommands(bot))
    await bot.tree.sync()
    logging.info("✅ BGA commands loaded and synced")
