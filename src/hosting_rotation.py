import discord
from discord.ext import commands
import logging
from pathlib import Path
from src.database import Database

# Setup Logging for Commands
logger = logging.getLogger(__name__)

# Define Allowed Channel for Commands (Replace with your actual channel ID)
ALLOWED_CHANNEL_ID = 1315906887312605194  # Update this with your correct Discord channel ID

def in_allowed_channel():
    """Decorator to restrict commands to a specific channel."""
    async def predicate(ctx):
        return ctx.channel.id == ALLOWED_CHANNEL_ID
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

# Required Setup Function for Bot Extensions
async def setup(bot):
    await bot.add_cog(HostingRotationCommands(bot))
    logger.info("✅ HostingRotationCommands cog has been loaded.")