import os
import discord
from discord import app_commands
from discord.ext import commands
import logging
from pathlib import Path
from src.database import Database

# Setup Logging for Commands
logger = logging.getLogger(__name__)

# Define Allowed Channel for Commands
HOSTING_ROTATION_CHANNEL_ID = int(os.getenv("HOSTING_ROTATION_CHANNEL_ID", "0"))

def in_allowed_channel():
    """Decorator to restrict commands to a specific channel."""
    async def predicate(interaction: discord.Interaction):
        if interaction.channel_id != HOSTING_ROTATION_CHANNEL_ID:
            await interaction.response.send_message("❌ This command can only be used in the designated channel.", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

# Create a Database Instance
DB_DIR = Path("/data")
DB_PATH = DB_DIR / "database.db"
database = Database(DB_PATH)

class HostingRotationCommands(commands.Cog):
    """Commands for managing the game hosts."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="addhost", description="Adds a user to the host list")
    @app_commands.describe(member="The user to add to the host list")
    @in_allowed_channel()
    async def add_host(self, interaction: discord.Interaction, member: discord.Member):
        logger.info(f"🔄 Received command: /addhost {member.name} (ID: {member.id})")

        database.addHost(str(member.id), member.name)
        await interaction.response.send_message(
            f"✅ {member.name} has been added to the host list!"
        )
        logger.info(f"✅ Successfully added {member.name} (ID: {member.id}) to the host list.")

    @app_commands.command(name="removehost", description="Removes a user from the host list")
    @app_commands.describe(member="The user to remove from the host list")
    @in_allowed_channel()
    async def remove_host(self, interaction: discord.Interaction, member: discord.Member):
        logger.info(f"🔄 Received command: /removehost {member.name}")

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

    @app_commands.command(name="nexthost", description="Shows who's next in the list")
    @in_allowed_channel()
    async def next_host(self, interaction: discord.Interaction):
        logger.info("🔄 Received command: /nexthost")

        host = database.getNextHost()
        if host:
            await interaction.response.send_message(
                f"🎲 The next host is: **{host['username']}**"
            )
            logger.info(f"✅ Next host: {host['username']}")
        else:
            await interaction.response.send_message("❌ No active hosts found.")
            logger.warning("⚠️ No active hosts found.")

    @app_commands.command(name="movehost", description="Move a host to a specific position")
    @app_commands.describe(
        member="The user to move",
        position="Where to move them (top/bottom/next)",
    )
    @app_commands.choices(position=[
        app_commands.Choice(name="Top of list", value="top"),
        app_commands.Choice(name="Bottom of list", value="bottom"),
        app_commands.Choice(name="Next in line", value="next")
    ])
    @in_allowed_channel()
    async def move_host(self, interaction: discord.Interaction, member: discord.Member, position: app_commands.Choice[str]):
        logger.info(f"🔄 Received command: /movehost {member.name} to {position.value}")
        
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

    @app_commands.command(name="swaphosts", description="Swap the positions of two hosts")
    @app_commands.describe(first="First host", second="Second host")
    @in_allowed_channel()
    async def swap_hosts(self, interaction: discord.Interaction, first: discord.Member, second: discord.Member):
        logger.info(f"🔄 Received command: /swaphosts {first.name} {second.name}")
        
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

    @app_commands.command(name="rotate", description="Moves the current host to the bottom of the list")
    @in_allowed_channel()
    async def rotate(self, interaction: discord.Interaction):
        logger.info("🔄 Received command: /rotate")

        result = database.rotateHosts()
        await interaction.response.send_message("✅ Hosting rotation updated!")
        logger.info(f"✅ Hosting rotation has been updated. {result}")

    @app_commands.command(name="hostlist", description="Displays the current host list order")
    @in_allowed_channel()
    async def host_list(self, interaction: discord.Interaction):
        logger.info("🔄 Received command: /hostlist")

        hosts = database.getAllHosts()
        
        if hosts:
            embed = discord.Embed(
                title="🎲 Current Hosting Rotation",
                description="The current order of game hosts:",
                color=discord.Color.blue()
            )
            
            for host in hosts:
                embed.add_field(
                    name=f"{host['position']}. {host['username']}", 
                    value="\u200b",  # Zero-width space as value
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"✅ Displayed host list with {len(hosts)} hosts")
        else:
            await interaction.response.send_message("❌ No active hosts found.")
            logger.warning("⚠️ No active hosts found for host list.")

    @app_commands.command(name="hosthelp", description="Shows help information for all host commands")
    @in_allowed_channel()
    async def host_help(self, interaction: discord.Interaction):
        """Displays help information for all hosting commands."""
        logger.info("🔄 Received command: /hosthelp")
        
        embed = discord.Embed(
            title="🎲 Host List Commands",
            description="Here are all the commands available for managing the game host list:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📋 View Commands",
            value=(
                "**/nexthost** - Shows who's next in the list\n"
                "**/hostlist** - Displays the complete host order"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔄 List Management",
            value=(
                "**/rotate** - Moves current host to the bottom\n"
                "**/movehost @user [top/bottom/next]** - Move a host to a specific position\n"
                "**/swaphosts @user1 @user2** - Swaps the positions of two hosts"
            ),
            inline=False
        )
        
        embed.add_field(
            name="👤 User Management",
            value=(
                "**/addhost @user** - Adds a new user to the list\n"
                "**/removehost @user** - Removes a user from the list"
            ),
            inline=False
        )
        
        embed.set_footer(text="Commands must be used in the designated channel")
        
        await interaction.response.send_message(embed=embed)
        logger.info("✅ Displayed host help information")

async def setup(bot):
    await bot.add_cog(HostingRotationCommands(bot))
    await bot.tree.sync()
    logger.info("✅ HostingRotationCommands cog has been loaded and commands synced.")