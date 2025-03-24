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
    """Commands for managing the hosting rotation."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add_host", description="Adds a user to the hosting rotation")
    @app_commands.describe(member="The user to add to the hosting rotation")
    @in_allowed_channel()
    async def add_host(self, interaction: discord.Interaction, member: discord.Member):
        logger.info(f"🔄 Received command: /add_host {member.name} (ID: {member.id})")

        database.addHost(str(member.id), member.name)
        await interaction.response.send_message(
            f"✅ {member.name} has been added to the hosting rotation!"
        )
        logger.info(f"✅ Successfully added {member.name} (ID: {member.id}) to the hosting rotation.")

    @app_commands.command(name="next_host", description="Shows who's next in the rotation")
    @in_allowed_channel()
    async def next_host(self, interaction: discord.Interaction):
        logger.info("🔄 Received command: /next_host")

        host = database.getNextHost()
        if host:
            await interaction.response.send_message(
                f"🎲 The next host is: **{host['username']}**"
            )
            logger.info(f"✅ Next host: {host['username']}")
        else:
            await interaction.response.send_message("❌ No active hosts found.")
            logger.warning("⚠️ No active hosts found.")

    @app_commands.command(name="rotate_hosts", description="Moves the current host to the back of the queue")
    @in_allowed_channel()
    async def rotate_hosts(self, interaction: discord.Interaction):
        logger.info("🔄 Received command: /rotate_hosts")

        result = database.rotateHosts()
        await interaction.response.send_message("✅ Hosting rotation updated!")
        logger.info(f"✅ Hosting rotation has been updated. {result}")

    @app_commands.command(name="defer_host", description="Allows a user to defer their hosting turn")
    @app_commands.describe(member="The user who wants to defer their turn")
    @in_allowed_channel()
    async def defer_host(self, interaction: discord.Interaction, member: discord.Member):
        logger.info(f"🔄 Received command: /defer_host {member.name}")

        result = database.deferHost(str(member.id))
        await interaction.response.send_message(f"✅ {member.name} has deferred their turn.")
        logger.info(f"✅ {member.name} has deferred their hosting turn. {result}")

    @app_commands.command(name="snooze_host", description="Temporarily removes a user from the hosting rotation")
    @app_commands.describe(member="The user to snooze")
    @in_allowed_channel()
    async def snooze_host(self, interaction: discord.Interaction, member: discord.Member):
        logger.info(f"🔄 Received command: /snooze_host {member.name}")

        result = database.snoozeHost(str(member.id))
        await interaction.response.send_message(f"😴 {member.name} has been snoozed.")
        logger.info(f"✅ {member.name} has been snoozed. {result}")
    
    @app_commands.command(name="activate_host", description="Reactivates a snoozed user in the hosting rotation")
    @app_commands.describe(member="The user to reactivate")
    @in_allowed_channel()
    async def activate_host(self, interaction: discord.Interaction, member: discord.Member):
        logger.info(f"🔄 Received command: /activate_host {member.name}")

        result = database.activateHost(str(member.id))
        await interaction.response.send_message(f"🔔 {member.name} has been reactivated in the rotation.")
        logger.info(f"✅ {member.name} has been reactivated. {result}")

    @app_commands.command(name="rotation_list", description="Displays the current hosting rotation order")
    @in_allowed_channel()
    async def rotation_list(self, interaction: discord.Interaction):
        logger.info("🔄 Received command: /rotation_list")

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
                    value=f"Position: {host['position']}", 
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"✅ Displayed rotation list with {len(hosts)} hosts")
        else:
            await interaction.response.send_message("❌ No active hosts found in the rotation.")
            logger.warning("⚠️ No active hosts found for rotation list.")
            
    @app_commands.command(name="force_host", description="Force a user to the top of the hosting rotation")
    @app_commands.describe(member="The user to force to the top")
    @in_allowed_channel()
    async def force_host(self, interaction: discord.Interaction, member: discord.Member):
        logger.info(f"🔄 Received command: /force_host {member.name}")

        try:
            database.connect()
            cursor = database.cursor
            
            cursor.execute("SELECT username, order_position FROM hosting_rotation WHERE discord_id=? AND active=1", 
                           (str(member.id),))
            host = cursor.fetchone()
            if not host:
                await interaction.response.send_message(f"❌ {member.name} not found in active rotation.")
                logger.warning(f"Host {member.name} not found or not active for force command")
                database.close()
                return
                
            username, current_position = host
            logger.info(f"Found host {username} at position {current_position}")
            
            if current_position == 1:
                await interaction.response.send_message(f"ℹ️ {username} is already at the top of the rotation.")
                database.close()
                return
            
            cursor.execute("UPDATE hosting_rotation SET order_position = order_position + 1 WHERE order_position < ? AND active=1", 
                         (current_position,))
            
            cursor.execute("UPDATE hosting_rotation SET order_position = 1 WHERE discord_id = ?", 
                         (str(member.id),))
            
            database.conn.commit()
            database.close()
            
            await interaction.response.send_message(f"✅ {username} has been moved to the top of the rotation!")
            logger.info(f"✅ {username} has been moved to the top of the rotation")
            
        except Exception as e:
            logger.error(f"Error in force_host command: {e}")
            database.conn.rollback()
            database.close()
            await interaction.response.send_message("❌ An error occurred while processing this command.")

    @app_commands.command(name="swap_position", description="Swap the positions of two users in the hosting rotation")
    @app_commands.describe(member1="The first user", member2="The second user")
    @in_allowed_channel()
    async def swap_position(self, interaction: discord.Interaction, member1: discord.Member, member2: discord.Member):
        logger.info(f"🔄 Received command: /swap_position {member1.name} {member2.name}")
        
        try:
            database.connect()
            cursor = database.cursor
            
            cursor.execute("SELECT username, order_position FROM hosting_rotation WHERE discord_id=? AND active=1", 
                           (str(member1.id),))
            host1 = cursor.fetchone()
            
            cursor.execute("SELECT username, order_position FROM hosting_rotation WHERE discord_id=? AND active=1", 
                           (str(member2.id),))
            host2 = cursor.fetchone()
            
            if not host1 or not host2:
                missing = []
                if not host1:
                    missing.append(member1.name)
                if not host2:
                    missing.append(member2.name)
                    
                await interaction.response.send_message(f"❌ {', '.join(missing)} not found in active rotation.")
                logger.warning(f"Hosts not found or not active for swap command: {', '.join(missing)}")
                database.close()
                return
                
            username1, position1 = host1
            username2, position2 = host2
            
            logger.info(f"Swapping {username1} (position {position1}) with {username2} (position {position2})")
            
            cursor.execute("UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ?", 
                         (position2, str(member1.id)))
            cursor.execute("UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ?", 
                         (position1, str(member2.id)))
            
            database.conn.commit()
            database.close()
            
            await interaction.response.send_message(f"✅ Swapped positions of {username1} and {username2}!")
            logger.info(f"✅ Swapped positions of {username1} and {username2}")
            
        except Exception as e:
            logger.error(f"Error in swap_position command: {e}")
            database.conn.rollback()
            database.close()
            await interaction.response.send_message("❌ An error occurred while processing this command.")

    @app_commands.command(name="send_to_back", description="Send a user to the back of the hosting rotation")
    @app_commands.describe(member="The user to send to the back")
    @in_allowed_channel()
    async def send_to_back(self, interaction: discord.Interaction, member: discord.Member):
        logger.info(f"🔄 Received command: /send_to_back {member.name}")
        
        try:
            database.connect()
            cursor = database.cursor
            
            cursor.execute("SELECT username, order_position FROM hosting_rotation WHERE discord_id=? AND active=1", 
                           (str(member.id),))
            host = cursor.fetchone()
            if not host:
                await interaction.response.send_message(f"❌ {member.name} not found in active rotation.")
                logger.warning(f"Host {member.name} not found or not active for send_to_back command")
                database.close()
                return
                
            username, current_position = host
            
            cursor.execute("SELECT MAX(order_position) FROM hosting_rotation WHERE active=1")
            max_position = cursor.fetchone()[0]
            
            if current_position == max_position:
                await interaction.response.send_message(f"ℹ️ {username} is already at the back of the rotation.")
                database.close()
                return
            
            logger.info(f"Moving {username} from position {current_position} to the back")
            
            cursor.execute("UPDATE hosting_rotation SET order_position = order_position - 1 WHERE order_position > ? AND active=1", 
                         (current_position,))
            
            cursor.execute("UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ?", 
                         (max_position, str(member.id)))
            
            database.conn.commit()
            database.close()
            
            await interaction.response.send_message(f"✅ {username} has been moved to the back of the rotation!")
            logger.info(f"✅ {username} has been moved to the back of the rotation")
            
        except Exception as e:
            logger.error(f"Error in send_to_back command: {e}")
            database.conn.rollback()
            database.close()
            await interaction.response.send_message("❌ An error occurred while processing this command.")

    @app_commands.command(name="hosting_help", description="Shows help information for all hosting commands")
    @in_allowed_channel()
    async def hosting_help(self, interaction: discord.Interaction):
        """Displays help information for all hosting rotation commands."""
        logger.info("🔄 Received command: /hosting_help")
        
        embed = discord.Embed(
            title="🎲 Hosting Rotation Commands",
            description="Here are all the commands available for managing the game hosting rotation:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📋 View Commands",
            value=(
                "**/next_host** - Shows who's next in the rotation\n"
                "**/rotation_list** - Displays the complete hosting order"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔄 Rotation Commands",
            value=(
                "**/rotate_hosts** - Moves the current host to the back\n"
                "**/defer_host @user** - User keeps their position but skips their turn\n"
                "**/force_host @user** - Moves user to the top of the rotation\n"
                "**/send_to_back @user** - Moves user to the end of the rotation\n"
                "**/swap_position @user1 @user2** - Swaps the positions of two users"
            ),
            inline=False
        )
        
        embed.add_field(
            name="👤 User Management",
            value=(
                "**/add_host @user** - Adds a new user to the rotation\n"
                "**/snooze_host @user** - Temporarily removes user from rotation\n"
                "**/activate_host @user** - Brings a snoozed user back into rotation"
            ),
            inline=False
        )
        
        embed.add_field(
            name="❓ Help",
            value="**/hosting_help** - Shows this help message",
            inline=False
        )
        
        embed.set_footer(text="Commands must be used in the designated channel")
        
        await interaction.response.send_message(embed=embed)
        logger.info("✅ Displayed hosting help information")

async def setup(bot):
    await bot.add_cog(HostingRotationCommands(bot))
    await bot.tree.sync()
    logger.info("✅ HostingRotationCommands cog has been loaded and commands synced.")