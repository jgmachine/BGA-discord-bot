import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime
from ..database import events_db

class EventCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.event_refresh.start()

    def cog_unload(self):
        self.event_refresh.cancel()

    @app_commands.command(name="event_add")
    @app_commands.default_permissions(administrator=True)
    async def event_add(self, interaction: discord.Interaction, url: str):
        """Add an Aftergame event URL to track"""
        if 'aftergame.co/events/' not in url:
            await interaction.response.send_message('Please provide a valid Aftergame event URL.')
            return
            
        if events_db.add_event(self.bot.db_conn, url):
            await events_db.update_event(self.bot.db_conn, url)
            await interaction.response.send_message('Event added and data updated.')
        else:
            await interaction.response.send_message('Failed to add event.')

    @app_commands.command(name="event_remove")
    @app_commands.default_permissions(administrator=True)
    async def event_remove(self, interaction: discord.Interaction, url: str):
        """Remove an Aftergame event URL from tracking"""
        if events_db.remove_event(self.bot.db_conn, url):
            await interaction.response.send_message('Event removed.')
        else:
            await interaction.response.send_message('Failed to remove event.')

    @app_commands.command(name="event_list")
    async def event_list(self, interaction: discord.Interaction):
        """List all tracked events"""
        events = events_db.get_all_events(self.bot.db_conn)
        if not events:
            await interaction.response.send_message('No events are being tracked.')
            return
            
        embed = discord.Embed(title="Tracked Events", color=discord.Color.blue())
        for event in events:
            embed.add_field(
                name=f"{event['name']} - {event['date'].strftime('%Y-%m-%d %H:%M')}",
                value=f"Venue: {event['venue']}\nGoing: {event['going_count']}\n[Link]({event['url']})",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="event_next")
    async def event_next(self, interaction: discord.Interaction):
        """Show the next upcoming event"""
        event = events_db.get_next_event(self.bot.db_conn)
        if not event:
            await interaction.response.send_message('No upcoming events found.')
            return
            
        embed = discord.Embed(
            title=event['name'],
            url=event['url'],
            color=discord.Color.blue()
        )
        embed.add_field(name="Date", value=event['date'].strftime('%Y-%m-%d %H:%M'))
        if event['venue']:
            embed.add_field(name="Venue", value=event['venue'])
        if event['address']:
            embed.add_field(name="Address", value=event['address'])
        embed.add_field(name="Going", value=str(event['going_count']))
        if event['image_url']:
            embed.set_image(url=event['image_url'])
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="event_refresh")
    @app_commands.default_permissions(administrator=True)
    async def event_refresh(self, interaction: discord.Interaction):
        """Manually refresh event data"""
        await interaction.response.send_message('Refreshing event data...')
        await events_db.update_all_events(self.bot.db_conn)
        await interaction.followup.send('Event data refreshed.')

    @tasks.loop(hours=1)
    async def event_refresh(self):
        """Automatically refresh event data periodically"""
        if self.bot.db_conn:
            await events_db.update_all_events(self.bot.db_conn)

async def setup(bot):
    await bot.add_cog(EventCommands(bot))
