import logging
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

from src.database import Database
from src.config import Config

logger = logging.getLogger(__name__)

def host_command():
    """Combined decorator for host commands."""
    def decorator(func):
        return app_commands.command()(
            app_commands.guild_only()(  # Keep guild_only
                func  # Remove default_permissions(administrator=True) to allow visibility based on Discord's integration settings
            )
        )
    return decorator

class HostingRotationCommands(commands.Cog):
    """Commands for managing the game hosts."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.load()  # Load config per instance
        self.database = Database(self.config.database_path)  # Create database per instance
        self.hosting_rotation_channel_id = self.config.hosting_rotation_channel_id

    @host_command()
    @app_commands.describe(member="The user to add to the host list")
    async def host_add(self, interaction: discord.Interaction, member: discord.Member):
        """Adds a user to the host list"""
        logger.info(f"🔄 Received command: /host_add {member.name} (ID: {member.id})")

        self.database.add_host(str(member.id), member.name)
        await interaction.response.send_message(
            f"✅ {member.name} has been added to the host list!"
        )
        logger.info(f"✅ Successfully added {member.name} (ID: {member.id}) to the host list.")

    @host_command()
    @app_commands.describe(member="The user to remove from the host list")
    async def host_remove(self, interaction: discord.Interaction, member: discord.Member):
        """Removes a user from the host list"""
        logger.info(f"🔄 Received command: /host_remove {member.name}")

        try:
            self.database.connect()
            cursor = self.database.cursor

            cursor.execute("DELETE FROM hosting_rotation WHERE discord_id=?", (str(member.id),))
            if cursor.rowcount == 0:
                await interaction.response.send_message(f"❌ {member.name} is not in the host list.")
                return

            self.database.conn.commit()
            await interaction.response.send_message(f"✅ {member.name} has been removed from the host list.")
            logger.info(f"✅ Removed {member.name} from the host list")

        except sqlite3.Error as e:
            logger.error(f"Database error removing host {member.id}: {e}")
            self.database.conn.rollback()
            await interaction.response.send_message("❌ A database error occurred while processing this command.")
        except Exception:
            logger.exception(f"Unexpected error removing host {member.id}")
            self.database.conn.rollback()
            await interaction.response.send_message("❌ An unexpected error occurred while processing this command.")
        finally:
            self.database.close()

    @host_command()
    async def host_next(self, interaction: discord.Interaction):
        """Shows who's next in the list"""
        logger.info("🔄 Received command: /host_next")

        host = self.database.get_next_host()
        if host:
            await interaction.response.send_message(
                f"🎲 The next host is: **{host['username']}**"
            )
            logger.info(f"✅ Next host: {host['username']}")
        else:
            await interaction.response.send_message("❌ No active hosts found.")
            logger.warning("⚠️ No active hosts found.")

    @host_command()
    @app_commands.describe(
        member="The user to move",
        position="Where to move them (top/bottom/next)",
    )
    @app_commands.choices(position=[
        app_commands.Choice(name="Top of list", value="top"),
        app_commands.Choice(name="Bottom of list", value="bottom"),
        app_commands.Choice(name="Next in line", value="next")
    ])
    async def host_move(self, interaction: discord.Interaction, member: discord.Member, position: app_commands.Choice[str]):
        """Move a host to a specific position"""
        logger.info(f"🔄 Received command: /host_move {member.name} to {position.value}")
        
        try:
            result = self.database.move_host(str(member.id), position.value, host_type_id=1)
            await interaction.response.send_message(f"✅ {result}")
            logger.info(f"✅ Successfully moved {member.name} to {position.value}")
        except sqlite3.Error as e:
            logger.error(f"Database error moving host {member.id}: {e}")
            await interaction.response.send_message("❌ A database error occurred while processing this command.")
        except Exception:
            logger.exception(f"Unexpected error moving host {member.id}")
            await interaction.response.send_message("❌ An unexpected error occurred while processing this command.")

    @host_command()
    @app_commands.describe(first="First host", second="Second host")
    async def host_swap(self, interaction: discord.Interaction, first: discord.Member, second: discord.Member):
        """Swap the positions of two hosts"""
        logger.info(f"🔄 Received command: /host_swap {first.name} {second.name}")
        
        try:
            self.database.connect()
            cursor = self.database.cursor

            cursor.execute("SELECT username, order_position FROM hosting_rotation WHERE discord_id=? AND active=1",
                           (str(first.id),))
            host1 = cursor.fetchone()

            cursor.execute("SELECT username, order_position FROM hosting_rotation WHERE discord_id=? AND active=1",
                           (str(second.id),))
            host2 = cursor.fetchone()

            if not host1 or not host2:
                missing = []
                if not host1:
                    missing.append(first.name)
                if not host2:
                    missing.append(second.name)

                await interaction.response.send_message(f"❌ {', '.join(missing)} not found in active rotation.")
                logger.warning(f"Hosts not found or not active for swap command: {', '.join(missing)}")
                self.database.close()
                return

            username1, position1 = host1
            username2, position2 = host2

            logger.info(f"Swapping {username1} (position {position1}) with {username2} (position {position2})")

            cursor.execute("UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ?",
                         (position2, str(first.id)))
            cursor.execute("UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ?",
                         (position1, str(second.id)))

            self.database.conn.commit()
            self.database.close()

            await interaction.response.send_message(f"✅ Swapped positions of {username1} and {username2}!")
            logger.info(f"✅ Swapped positions of {username1} and {username2}")

        except sqlite3.Error as e:
            logger.error(f"Database error in swap_position command: {e}")
            self.database.conn.rollback()
            self.database.close()
            await interaction.response.send_message("❌ A database error occurred while processing this command.")
        except Exception:
            logger.exception("Unexpected error in swap_position command")
            self.database.conn.rollback()
            self.database.close()
            await interaction.response.send_message("❌ An unexpected error occurred while processing this command.")

    @host_command()
    async def host_rotate(self, interaction: discord.Interaction):
        """Moves the current host to the bottom of the list"""
        logger.info("🔄 Received command: /host_rotate")

        result = self.database.rotate_hosts()
        await interaction.response.send_message("✅ Hosting rotation updated!")
        logger.info(f"✅ Hosting rotation has been updated. {result}")

    @host_command()
    async def host_list(self, interaction: discord.Interaction):
        """Displays both venue and game host rotations"""
        logger.info("🔄 Received command: /host_list")

        venue_hosts = self.database.get_all_hosts(host_type_id=1)
        game_hosts = self.database.get_all_hosts(host_type_id=2)
        
        embed = discord.Embed(
            title="🏡 Hosting Schedule",
            description="Current venue hosts and secondary game hosts rotations",
            color=discord.Color.blue()
        )

        # Show current/next hosts at the top
        if venue_hosts:
            next_venue = venue_hosts[0]['username']
            embed.add_field(
                name="📍 Next Venue Host",
                value=f"**{next_venue}** will host the next event",
                inline=False
            )

            # Find first game host who isn't the venue host
            next_game_host = next((host['username'] for host in game_hosts 
                                 if host['username'] != next_venue), None)
            if next_game_host:
                embed.add_field(
                    name="🎲 Available Game Host",
                    value=f"**{next_game_host}** can host a second game if needed",
                    inline=False
                )
            embed.add_field(name="\u200b", value="\u200b", inline=False)  # Spacer

        # Show full rotations side by side
        venue_list = "\n".join([f"{h['position']}. {h['username']}" for h in venue_hosts]) if venue_hosts else "No venue hosts"
        game_list = "\n".join([f"{h['position']}. {h['username']}" for h in game_hosts]) if game_hosts else "No game hosts"
        
        embed.add_field(
            name="📋 Venue Host Rotation",
            value=venue_list,
            inline=True
        )
        embed.add_field(
            name="🎲 Game Host Rotation",
            value=game_list,
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)
        logger.info(f"✅ Displayed host list with {len(venue_hosts)} venue hosts and {len(game_hosts)} game hosts")

    @host_command()
    async def host_help(self, interaction: discord.Interaction):
        """Shows help information for all host commands"""
        logger.info("🔄 Received command: /host_help")
        
        embed = discord.Embed(
            title="🎲 Hosting Commands",
            description="Commands for managing both venue and game host rotations:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📋 Venue Host Commands",
            value=(
                "**/host_next** - Shows who's next to host venue\n"
                "**/host_list** - Shows venue host rotation\n"
                "**/host_rotate** - Moves current venue host to bottom\n"
                "**/host_move @user [top/bottom/next]** - Move venue host position\n"
                "**/host_swap @user1 @user2** - Swap venue hosts\n"
                "**/host_add @user** - Add venue host\n"
                "**/host_remove @user** - Remove venue host"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🎲 Game Host Commands",
            value=(
                "**/host2_next** - Shows who's next to host game\n"
                "**/host2_list** - Shows game host rotation\n"
                "**/host2_rotate** - Moves current game host to bottom\n"
                "**/host2_move @user [top/bottom/next]** - Move game host position\n"
                "**/host2_add @user** - Add game host\n"
                "**/host2_remove @user** - Remove game host"
            ),
            inline=False
        )
        
        embed.set_footer(text="Commands must be used in the designated channel")
        await interaction.response.send_message(embed=embed)
        logger.info("✅ Displayed hosting help information")

class SecondaryHostCommands(commands.Cog):
    """Commands for managing the secondary game hosts."""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.load()
        self.database = Database(self.config.database_path)
        self.hosting_rotation_channel_id = self.config.hosting_rotation_channel_id

    @host_command()
    @app_commands.describe(member="The user to add to the game host list")
    async def host2_add(self, interaction: discord.Interaction, member: discord.Member):
        """Adds a user to the secondary game host list"""
        logger.info(f"🔄 Adding secondary host: {member.name}")
        
        try:
            # Remove debug_schema call since we've confirmed schema is correct
            success = self.database.add_host(str(member.id), member.name, host_type_id=2)
            if success:
                await interaction.response.send_message(
                    f"✅ {member.name} has been added to the game host list!"
                )
            else:
                await interaction.response.send_message(
                    f"❌ Failed to add {member.name} to the game host list."
                )
        except sqlite3.Error as e:
            logger.error(f"Database error adding game host {member.id}: {e}")
            await interaction.response.send_message(
                "❌ A database error occurred while adding the game host. Check the logs for details."
            )
        except Exception:
            logger.exception(f"Unexpected error adding game host {member.id}")
            await interaction.response.send_message(
                "❌ An unexpected error occurred while adding the game host. Check the logs for details."
            )

    @host_command()
    @app_commands.describe(member="The user to remove from the game host list")
    async def host2_remove(self, interaction: discord.Interaction, member: discord.Member):
        """Removes a user from the game host list"""
        logger.info(f"🔄 Removing secondary host: {member.name}")
        try:
            cursor = self._execute(
                "UPDATE hosting_rotation SET game_active=0, game_position=NULL WHERE discord_id=?",
                (str(member.id),)
            )
            if cursor.rowcount == 0:
                await interaction.response.send_message(f"❌ {member.name} is not in the game host list.")
                return
            await interaction.response.send_message(f"✅ {member.name} has been removed from the game host list.")
        except sqlite3.Error as e:
            logger.error(f"Database error removing game host {member.id}: {e}")
            await interaction.response.send_message("❌ A database error occurred while processing this command.")
        except Exception:
            logger.exception(f"Unexpected error removing game host {member.id}")
            await interaction.response.send_message("❌ An unexpected error occurred while processing this command.")

    @host_command()
    async def host2_next(self, interaction: discord.Interaction):
        """Shows who's next in the game host list"""
        host = self.database.get_next_host(host_type_id=2)
        if host:
            await interaction.response.send_message(
                f"🎲 The next game host is: **{host['username']}**"
            )
        else:
            await interaction.response.send_message("❌ No active game hosts found.")

    @host_command()
    async def host2_rotate(self, interaction: discord.Interaction):
        """Moves the current game host to the bottom of the list"""
        result = self.database.rotate_hosts(host_type_id=2)
        await interaction.response.send_message("✅ Game host rotation updated!")
        logger.info(f"✅ Game host rotation has been updated. {result}")

    @host_command()
    async def host2_list(self, interaction: discord.Interaction):
        """Displays the current game host list order"""
        hosts = self.database.get_all_hosts(host_type_id=2)
        
        if hosts:
            embed = discord.Embed(
                title="🎲 Current Game Host Rotation",
                description="\n".join([f"{host['position']}. {host['username']}" for host in hosts]),
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ No active game hosts found.")

    @host_command()
    @app_commands.describe(
        member="The user to move",
        position="Where to move them (top/bottom/next)",
    )
    @app_commands.choices(position=[
        app_commands.Choice(name="Top of list", value="top"),
        app_commands.Choice(name="Bottom of list", value="bottom"),
        app_commands.Choice(name="Next in line", value="next")
    ])
    async def host2_move(self, interaction: discord.Interaction, member: discord.Member, position: app_commands.Choice[str]):
        """Move a game host to a specific position"""
        logger.info(f"🔄 Received command: /host2_move {member.name} to {position.value}")
        
        try:
            result = self.database.move_host(str(member.id), position.value, host_type_id=2)
            await interaction.response.send_message(f"✅ {result}")
            logger.info(f"✅ Successfully moved {member.name} to {position.value}")
        except sqlite3.Error as e:
            logger.error(f"Database error moving game host {member.id}: {e}")
            await interaction.response.send_message("❌ A database error occurred while moving the game host.")
        except Exception:
            logger.exception(f"Unexpected error moving game host {member.id}")
            await interaction.response.send_message("❌ An unexpected error occurred while moving the game host.")

async def setup(bot):
    cfg = Config.load()
    if not cfg.hosting_rotation_channel_id:
        raise RuntimeError(
            "HOSTING_ROTATION_CHANNEL_ID is not set; hosting rotation commands cannot be restricted to a channel."
        )
    await bot.add_cog(HostingRotationCommands(bot))
    await bot.add_cog(SecondaryHostCommands(bot))
    logger.info("✅ Hosting rotation commands loaded")