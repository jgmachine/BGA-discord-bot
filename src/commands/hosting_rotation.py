import discord
from discord.ext import commands
from src.database import add_host, get_next_host, rotate_hosts, defer_host, snooze_host

ALLOWED_CHANNEL_ID = 1315906887312605194  # Replace with your actual channel ID

def in_allowed_channel():
    async def predicate(ctx):
        return ctx.channel.id == ALLOWED_CHANNEL_ID
    return commands.check(predicate)

class HostingRotationCommands(commands.Cog):
    """Commands for managing the hosting rotation."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @in_allowed_channel()
    async def add_host(self, ctx, member: discord.Member):
        """Adds a user to the hosting rotation."""
        add_host(str(member.id), member.name)
        await ctx.send(f"✅ {member.name} has been added to the hosting rotation!")

    @commands.command()
    @in_allowed_channel()
    async def next_host(self, ctx):
        """Displays the next host in the rotation."""
        host = get_next_host()
        if host:
            await ctx.send(f"🎲 The next host is: **{host}**")
        else:
            await ctx.send("❌ No active hosts found.")

    @commands.command()
    @in_allowed_channel()
    async def rotate_hosts(self, ctx):
        """Moves the current host to the back of the queue."""
        rotate_hosts()
        await ctx.send("✅ Hosting rotation updated!")

    @commands.command()
    @in_allowed_channel()
    async def defer_host(self, ctx, member: discord.Member):
        """Allows a user to defer their hosting turn."""
        defer_host(str(member.id))
        await ctx.send(f"✅ {member.name} has deferred their turn.")

    @commands.command()
    @in_allowed_channel()
    async def snooze_host(self, ctx, member: discord.Member):
        """Temporarily removes a user from the hosting rotation."""
        snooze_host(str(member.id))
        await ctx.send(f"😴 {member.name} has been snoozed.")

# Function to load the commands
async def setup(bot):
    await bot.add_cog(HostingRotationCommands(bot))
