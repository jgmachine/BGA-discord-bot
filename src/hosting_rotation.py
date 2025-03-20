import discord
from discord.ext import commands
import src.database as db  # ✅ Import database module properly

# ✅ Define Allowed Channel for Commands (Replace with your actual channel ID)
ALLOWED_CHANNEL_ID = 1315906887312605194  # 🔴 Update this with your correct Discord channel ID

def in_allowed_channel():
    """Decorator to restrict commands to a specific channel."""
    async def predicate(ctx):
        return ctx.channel.id == ALLOWED_CHANNEL_ID
    return commands.check(predicate)

# ✅ Create a Database Instance
database = db.Database(db.DB_PATH)  # Use the database class instance

class HostingRotationCommands(commands.Cog):
    """Commands for managing the hosting rotation."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @in_allowed_channel()
    async def add_host(self, ctx, member: discord.Member):
        """Adds a user to the hosting rotation."""
        database.add_host(str(member.id), member.name)  # ✅ Corrected function call
        await ctx.send(f"✅ {member.name} has been added to the hosting rotation!")

    @commands.command()
    @in_allowed_channel()
    async def next_host(self, ctx):
        """Displays the next host in the rotation."""
        host = database.get_next_host()  # ✅ Call method from database instance
        if host:
            await ctx.send(f"🎲 The next host is: **{host}**")
        else:
            await ctx.send("❌ No active hosts found.")

    @commands.command()
    @in_allowed_channel()
    async def rotate_hosts(self, ctx):
        """Moves the current host to the back of the queue."""
        database.rotate_hosts()  # ✅ Call method from database instance
        await ctx.send("✅ Hosting rotation updated!")

    @commands.command()
    @in_allowed_channel()
    async def defer_host(self, ctx, member: discord.Member):
        """Allows a user to defer their hosting turn."""
        database.defer_host(str(member.id))  # ✅ Call method from database instance
        await ctx.send(f"✅ {member.name} has deferred their turn.")

    @commands.command()
    @in_allowed_channel()
    async def snooze_host(self, ctx, member: discord.Member):
        """Temporarily removes a user from the hosting rotation."""
        database.snooze_host(str(member.id))  # ✅ Call method from database instance
        await ctx.send(f"😴 {member.name} has been snoozed.")

# ✅ Required Setup Function for Bot Extensions
async def setup(bot):
    await bot.add_cog(HostingRotationCommands(bot))
