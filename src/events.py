import discord
from discord import app_commands
from discord.ext import commands, tasks
import logging
from datetime import datetime
from .database import events_db
from .config import Config
from .database import Database

logger = logging.getLogger(__name__)

def event_command():
    """Combined decorator for event commands."""
    def decorator(func):
        return app_commands.command()(
            app_commands.guild_only()(func)
        )
    return decorator

class EventCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.load()
        self.database = Database(self.config.database_path)
        self.database.connect()  # Ensure database is connected on init
        self.event_refresh.start()

    def cog_unload(self):
        self.event_refresh.cancel()
        self.database.close()  # Close database connection on unload

    @event_command()
    @app_commands.describe(url="The Aftergame event URL to track")
    async def event_add(self, interaction: discord.Interaction, url: str):
        """Add an Aftergame event URL to track"""
        if 'aftergame.co/events/' not in url:
            await interaction.response.send_message('Please provide a valid Aftergame event URL.')
            return
            
        if events_db.add_event(self.database.conn, url):
            await events_db.update_event(self.database.conn, url)
            await interaction.response.send_message('Event added and data updated.')
        else:
            await interaction.response.send_message('Failed to add event.')

    @event_command()
    @app_commands.describe(url="The Aftergame event URL to remove")
    async def event_remove(self, interaction: discord.Interaction, url: str):
        """Remove an Aftergame event URL from tracking"""
        if events_db.remove_event(self.database.conn, url):
            await interaction.response.send_message('Event removed.')
        else:
            await interaction.response.send_message('Failed to remove event.')

    @event_command()
    async def event_list(self, interaction: discord.Interaction):
        """List all tracked events"""
        events = events_db.get_all_events(self.database.conn)
        if not events:
            await interaction.response.send_message('No events are being tracked.')
            return
            
        embed = discord.Embed(title="Tracked Events", color=discord.Color.blue())
        for event in events:
            embed.add_field(
                name=f"{event['name']} - {event['date'].strftime('%A, %B %d at %I:%M %p %Z')}",
                value=f"Venue: {event['venue']}\nGoing: {event['going_count']}\n[Link]({event['url']})",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    @event_command()
    async def event_next(self, interaction: discord.Interaction):
        """Show the next upcoming event"""
        event = events_db.get_next_event(self.database.conn)
        if not event:
            await interaction.response.send_message('No upcoming events found.')
            return
            
        embed = discord.Embed(
            title=event['name'],
            url=event['url'],
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Date", 
            value=event['date'].strftime('%A, %B %d at %I:%M %p %Z')
        )
        if event['venue']:
            embed.add_field(name="Venue", value=event['venue'])
        if event['address']:
            embed.add_field(name="Address", value=event['address'])
        embed.add_field(name="Going", value=str(event['going_count']))
        if event['image_url']:
            embed.set_image(url=event['image_url'])
        await interaction.response.send_message(embed=embed)

    @event_command()
    async def event_refresh(self, interaction: discord.Interaction):
        """Manually refresh event data"""
        await interaction.response.send_message('Refreshing event data...')
        await events_db.update_all_events(self.database.conn)
        await interaction.followup.send('Event data refreshed.')

    @tasks.loop(minutes=15)
    async def event_refresh(self):
        """Automatically refresh event data periodically"""
        if self.database and self.database.conn:
            await events_db.update_all_events(self.database.conn)

async def setup(bot):
    await bot.add_cog(EventCommands(bot))
    logger.info("✅ Event commands loaded")
