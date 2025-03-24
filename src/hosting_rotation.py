import os
import discord
from discord.ext import commands
import logging
from pathlib import Path
from src.database import Database

# Setup Logging for Commands
logger = logging.getLogger(__name__)

# Define Allowed Channel for Commands (Replace with your actual channel ID)
HOSTING_ROTATION_CHANNEL_ID = int(os.getenv("HOSTING_ROTATION_CHANNEL_ID", "0"))

def in_allowed_channel():
    """Decorator to restrict commands to a specific channel."""
    async def predicate(ctx):
        return ctx.channel.id == HOSTING_ROTATION_CHANNEL_ID
    return commands.check(predicate)

# Create a Database Instance - Use the DB_PATH from database.py correctly
DB_DIR = Path("/data")
DB_PATH = DB_DIR / "database.db"
database = Database(DB_PATH)  # Use the database class with proper path

class HostingRotationCommands(commands.Cog):
    """Commands for managing the hosting rotation."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @in_allowed_channel()
    async def add_host(self, ctx, member: discord.Member):
        """Adds a user to the hosting rotation."""
        logger.info(f"🔄 Received command: !add_host {member.name} (ID: {member.id})")

        # Fix: Use camelCase function name to match database.py implementation
        database.addHost(str(member.id), member.name)
        await ctx.send(f"✅ {member.name} has been added to the hosting rotation!")

        # Log confirmation
        logger.info(f"✅ Successfully added {member.name} (ID: {member.id}) to the hosting rotation.")

    @commands.command()
    @in_allowed_channel()
    async def next_host(self, ctx):
        """Displays the next host in the rotation."""
        logger.info("🔄 Received command: !next_host")

        # Fix: Use camelCase function name to match database.py implementation
        host = database.getNextHost()
        if host:
            await ctx.send(f"🎲 The next host is: **{host['username']}**")
            logger.info(f"✅ Next host: {host['username']}")
        else:
            await ctx.send("❌ No active hosts found.")
            logger.warning("⚠️ No active hosts found.")

    @commands.command()
    @in_allowed_channel()
    async def rotate_hosts(self, ctx):
        """Moves the current host to the back of the queue."""
        logger.info("🔄 Received command: !rotate_hosts")

        # Fix: Use camelCase function name to match database.py implementation
        result = database.rotateHosts()
        await ctx.send("✅ Hosting rotation updated!")
        logger.info(f"✅ Hosting rotation has been updated. {result}")

    @commands.command()
    @in_allowed_channel()
    async def defer_host(self, ctx, member: discord.Member):
        """Allows a user to defer their hosting turn."""
        logger.info(f"🔄 Received command: !defer_host {member.name}")

        # Fix: Use camelCase function name to match database.py implementation
        result = database.deferHost(str(member.id))
        await ctx.send(f"✅ {member.name} has deferred their turn.")
        logger.info(f"✅ {member.name} has deferred their hosting turn. {result}")

    @commands.command()
    @in_allowed_channel()
    async def snooze_host(self, ctx, member: discord.Member):
        """Temporarily removes a user from the hosting rotation."""
        logger.info(f"🔄 Received command: !snooze_host {member.name}")

        # Fix: Use camelCase function name to match database.py implementation
        result = database.snoozeHost(str(member.id))
        await ctx.send(f"😴 {member.name} has been snoozed.")
        logger.info(f"✅ {member.name} has been snoozed. {result}")
    
    @commands.command()
    @in_allowed_channel()
    async def activate_host(self, ctx, member: discord.Member):
        """Reactivates a snoozed user in the hosting rotation."""
        logger.info(f"🔄 Received command: !activate_host {member.name}")

        # Fix: Use camelCase function name to match database.py implementation
        result = database.activateHost(str(member.id))
        await ctx.send(f"🔔 {member.name} has been reactivated in the rotation.")
        logger.info(f"✅ {member.name} has been reactivated. {result}")

    @commands.command()
    @in_allowed_channel()
    async def rotation_list(self, ctx):
        """Displays the current hosting rotation order."""
        logger.info("🔄 Received command: !rotation_list")

        # Get all hosts in rotation order
        hosts = database.getAllHosts()
        
        if hosts:
            # Create an embedded message for nicer formatting
            embed = discord.Embed(
                title="🎲 Current Hosting Rotation",
                description="The current order of game hosts:",
                color=discord.Color.blue()
            )
            
            # Add hosts to the embed
            for host in hosts:
                embed.add_field(
                    name=f"{host['position']}. {host['username']}", 
                    value=f"Position: {host['position']}", 
                    inline=False
                )
            
            await ctx.send(embed=embed)
            logger.info(f"✅ Displayed rotation list with {len(hosts)} hosts")
        else:
            await ctx.send("❌ No active hosts found in the rotation.")
            logger.warning("⚠️ No active hosts found for rotation list.")
            
    @commands.command()
    @in_allowed_channel()
    async def force_host(self, ctx, member: discord.Member):
        """Force a user to the top of the hosting rotation."""
        logger.info(f"🔄 Received command: !force_host {member.name}")

        try:
            database.connect()
            cursor = database.cursor
            
            # Verify the host exists and is active
            cursor.execute("SELECT username, order_position FROM hosting_rotation WHERE discord_id=? AND active=1", 
                           (str(member.id),))
            host = cursor.fetchone()
            if not host:
                await ctx.send(f"❌ {member.name} not found in active rotation.")
                logger.warning(f"Host {member.name} not found or not active for force command")
                database.close()
                return
                
            username, current_position = host
            logger.info(f"Found host {username} at position {current_position}")
            
            # If already at position 1, no need to change
            if current_position == 1:
                await ctx.send(f"ℹ️ {username} is already at the top of the rotation.")
                database.close()
                return
            
            # Increment everyone's position who is ahead of this user
            cursor.execute("UPDATE hosting_rotation SET order_position = order_position + 1 WHERE order_position < ? AND active=1", 
                         (current_position,))
            
            # Move this user to position 1
            cursor.execute("UPDATE hosting_rotation SET order_position = 1 WHERE discord_id = ?", 
                         (str(member.id),))
            
            database.conn.commit()
            database.close()
            
            await ctx.send(f"✅ {username} has been moved to the top of the rotation!")
            logger.info(f"✅ {username} has been moved to the top of the rotation")
            
        except Exception as e:
            logger.error(f"Error in force_host command: {e}")
            database.conn.rollback()
            database.close()
            await ctx.send("❌ An error occurred while processing this command.")

    @commands.command()
    @in_allowed_channel()
    async def swap_position(self, ctx, member1: discord.Member, member2: discord.Member):
        """Swap the positions of two users in the hosting rotation."""
        logger.info(f"🔄 Received command: !swap_position {member1.name} {member2.name}")
        
        try:
            database.connect()
            cursor = database.cursor
            
            # Verify both hosts exist and are active
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
                    
                await ctx.send(f"❌ {', '.join(missing)} not found in active rotation.")
                logger.warning(f"Hosts not found or not active for swap command: {', '.join(missing)}")
                database.close()
                return
                
            username1, position1 = host1
            username2, position2 = host2
            
            logger.info(f"Swapping {username1} (position {position1}) with {username2} (position {position2})")
            
            # Swap positions
            cursor.execute("UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ?", 
                         (position2, str(member1.id)))
            cursor.execute("UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ?", 
                         (position1, str(member2.id)))
            
            database.conn.commit()
            database.close()
            
            await ctx.send(f"✅ Swapped positions of {username1} and {username2}!")
            logger.info(f"✅ Swapped positions of {username1} and {username2}")
            
        except Exception as e:
            logger.error(f"Error in swap_position command: {e}")
            database.conn.rollback()
            database.close()
            await ctx.send("❌ An error occurred while processing this command.")

    @commands.command()
    @in_allowed_channel()
    async def send_to_back(self, ctx, member: discord.Member):
        """Send a user to the back of the hosting rotation."""
        logger.info(f"🔄 Received command: !send_to_back {member.name}")
        
        try:
            database.connect()
            cursor = database.cursor
            
            # Verify the host exists and is active
            cursor.execute("SELECT username, order_position FROM hosting_rotation WHERE discord_id=? AND active=1", 
                           (str(member.id),))
            host = cursor.fetchone()
            if not host:
                await ctx.send(f"❌ {member.name} not found in active rotation.")
                logger.warning(f"Host {member.name} not found or not active for send_to_back command")
                database.close()
                return
                
            username, current_position = host
            
            # Get the maximum position
            cursor.execute("SELECT MAX(order_position) FROM hosting_rotation WHERE active=1")
            max_position = cursor.fetchone()[0]
            
            # If already at the back, no need to change
            if current_position == max_position:
                await ctx.send(f"ℹ️ {username} is already at the back of the rotation.")
                database.close()
                return
            
            logger.info(f"Moving {username} from position {current_position} to the back")
            
            # Decrement everyone's position who is behind this user
            cursor.execute("UPDATE hosting_rotation SET order_position = order_position - 1 WHERE order_position > ? AND active=1", 
                         (current_position,))
            
            # Move this user to the back
            cursor.execute("UPDATE hosting_rotation SET order_position = ? WHERE discord_id = ?", 
                         (max_position, str(member.id)))
            
            database.conn.commit()
            database.close()
            
            await ctx.send(f"✅ {username} has been moved to the back of the rotation!")
            logger.info(f"✅ {username} has been moved to the back of the rotation")
            
        except Exception as e:
            logger.error(f"Error in send_to_back command: {e}")
            database.conn.rollback()
            database.close()
            await ctx.send("❌ An error occurred while processing this command.")

    @commands.command()
    @in_allowed_channel()
    async def hosting_help(self, ctx):
        """Displays help information for all hosting rotation commands."""
        logger.info("🔄 Received command: !hosting_help")
        
        # Create an embedded message for help information
        embed = discord.Embed(
            title="🎲 Hosting Rotation Commands",
            description="Here are all the commands available for managing the game hosting rotation:",
            color=discord.Color.blue()
        )
        
        # Basic commands
        embed.add_field(
            name="📋 View Commands",
            value=(
                "**`!next_host`** - Shows who's next in the rotation\n"
                "**`!rotation_list`** - Displays the complete hosting order"
            ),
            inline=False
        )
        
        # Rotation management
        embed.add_field(
            name="🔄 Rotation Commands",
            value=(
                "**`!rotate_hosts`** - Moves the current host to the back\n"
                "**`!defer_host @user`** - User keeps their position but skips their turn\n"
                "**`!force_host @user`** - Moves user to the top of the rotation\n"
                "**`!send_to_back @user`** - Moves user to the end of the rotation\n"
                "**`!swap_position @user1 @user2`** - Swaps the positions of two users"
            ),
            inline=False
        )
        
        # User management
        embed.add_field(
            name="👤 User Management",
            value=(
                "**`!add_host @user`** - Adds a new user to the rotation\n"
                "**`!snooze_host @user`** - Temporarily removes user from rotation\n"
                "**`!activate_host @user`** - Brings a snoozed user back into rotation"
            ),
            inline=False
        )
        
        # Help
        embed.add_field(
            name="❓ Help",
            value="**`!hosting_help`** - Shows this help message",
            inline=False
        )
        
        # Add a footer
        embed.set_footer(text="Commands must be used in the designated channel")
        
        await ctx.send(embed=embed)
        logger.info("✅ Displayed hosting help information")

# Required Setup Function for Bot Extensions
async def setup(bot):
    await bot.add_cog(HostingRotationCommands(bot))
    logger.info("✅ HostingRotationCommands cog has been loaded.")