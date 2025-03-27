import os
import discord
from discord import app_commands
from discord.ext import commands
import logging
from src.database import Database
from src.config import Config

logger = logging.getLogger(__name__)
config = Config.load()

# Use config values
HOSTING_ROTATION_CHANNEL_ID = config.hosting_rotation_channel_id
database = Database(config.database_path)

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

        database.add_host(str(member.id), member.name)
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
            database.connect()
            cursor = database.cursor
            
            cursor.execute("DELETE FROM hosting_rotation WHERE discord_id=?", (str(member.id),))
            if cursor.rowcount == 0:
                await interaction.response.send_message(f"❌ {member.name} is not in the host list.")
                return
                
            database.conn.commit()
            await interaction.response.send_message(f"✅ {member.name} has been removed from the host list.")
            logger.info(f"✅ Removed {member.name} from the host list")
            
        except Exception as e:
            logger.error(f"Error removing host: {e}")
            database.conn.rollback()
            await interaction.response.send_message("❌ An error occurred while processing this command.")
        finally:
            database.close()

    @host_command()
    async def host_next(self, interaction: discord.Interaction):
        """Shows who's next in the list"""
        logger.info("🔄 Received command: /host_next")

        host = database.get_next_host()
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
            database.connect()
            cursor = database.cursor
            
            # Verify host exists and is active
            cursor.execute("SELECT username, order_position FROM hosting_rotation WHERE discord_id=?", (str(member.id),))
            host = cursor.fetchone()
            if not host:
                await interaction.response.send_message(f"❌ {member.name} is not in the host list.")
                return
                
            username, current_pos = host
            
            if position.value == "top":
                # Move everyone else down one
                cursor.execute("UPDATE hosting_rotation SET order_position = order_position + 1")
                # Move target host to top
                cursor.execute("UPDATE hosting_rotation SET order_position = 1 WHERE discord_id = ?", (str(member.id),))
                msg = f"✅ {username} has been moved to the top of the list!"
                
            elif position.value == "bottom":
                # Get max position
                cursor.execute("SELECT MAX(order_position) FROM hosting_rotation")
                max_pos = cursor.fetchone()[0]
                # Move others up if needed
                cursor.execute("UPDATE hosting_rotation SET order_position = order_position - 1 WHERE order_position > ?", 
                             (current_pos,))
                # Move target host to bottom
                cursor.execute("UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ?", 
                             (max_pos, str(member.id),))
                msg = f"✅ {username} has been moved to the bottom of the list!"
                
            else:  # next
                # Move to position 2 (right after current host)
                cursor.execute("UPDATE hosting_rotation SET order_position = order_position + 1 WHERE order_position > 1")
                cursor.execute("UPDATE hosting_rotation SET order_position = 2 WHERE discord_id = ?", (str(member.id),))
                msg = f"✅ {username} will host next!"
            
            database.conn.commit()
            await interaction.response.send_message(msg)
            logger.info(f"✅ Successfully moved {username} to {position.value}")
            
        except Exception as e:
            logger.error(f"Error moving host: {e}")
            database.conn.rollback()
            await interaction.response.send_message("❌ An error occurred while processing this command.")
        finally:
            database.close()

    @host_command()
    @app_commands.describe(first="First host", second="Second host")
    async def host_swap(self, interaction: discord.Interaction, first: discord.Member, second: discord.Member):
        """Swap the positions of two hosts"""
        logger.info(f"🔄 Received command: /host_swap {first.name} {second.name}")
        
        try:
            database.connect()
            cursor = database.cursor
            
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
                database.close()
                return
                
            username1, position1 = host1
            username2, position2 = host2
            
            logger.info(f"Swapping {username1} (position {position1}) with {username2} (position {position2})")
            
            cursor.execute("UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ?", 
                         (position2, str(first.id)))
            cursor.execute("UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ?", 
                         (position1, str(second.id)))
            
            database.conn.commit()
            database.close()
            
            await interaction.response.send_message(f"✅ Swapped positions of {username1} and {username2}!")
            logger.info(f"✅ Swapped positions of {username1} and {username2}")
            
        except Exception as e:
            logger.error(f"Error in swap_position command: {e}")
            database.conn.rollback()
            database.close()
            await interaction.response.send_message("❌ An error occurred while processing this command.")

    @host_command()
    async def host_rotate(self, interaction: discord.Interaction):
        """Moves the current host to the bottom of the list"""
        logger.info("🔄 Received command: /host_rotate")

        result = database.rotate_hosts()
        await interaction.response.send_message("✅ Hosting rotation updated!")
        logger.info(f"✅ Hosting rotation has been updated. {result}")

    @host_command()
    async def host_list(self, interaction: discord.Interaction):
        """Displays the current host list order"""
        logger.info("🔄 Received command: /host_list")

        hosts = database.get_all_hosts()
        
        if hosts:
            embed = discord.Embed(
                title="🎲 Current Hosting Rotation",
                description="\n".join([f"{host['position']}. {host['username']}" for host in hosts]),
                color=discord.Color.blue()
            )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"✅ Displayed host list with {len(hosts)} hosts")
        else:
            await interaction.response.send_message("❌ No active hosts found.")
            logger.warning("⚠️ No active hosts found for host list.")

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
        except Exception as e:
            logger.error(f"Error adding game host: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while adding the game host. Check the logs for details."
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
        except Exception as e:
            logger.error(f"Error removing game host: {e}")
            await interaction.response.send_message("❌ An error occurred while processing this command.")

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
        # Similar to host_move but use game_position and game_active fields
        # Implementation follows same pattern as host_move with host_type_id=2
        try:
            # Moving game host logic here
            result = self.database.move_host(str(member.id), position.value, host_type_id=2)
            await interaction.response.send_message(result)
        except Exception as e:
            logger.error(f"Error moving game host: {e}")
            await interaction.response.send_message("❌ An error occurred while moving the game host.")

async def setup(bot):
    await bot.add_cog(HostingRotationCommands(bot))
    await bot.add_cog(SecondaryHostCommands(bot))
    logger.info("✅ Hosting rotation commands loaded")