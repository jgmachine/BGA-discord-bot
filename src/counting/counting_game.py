import logging
import random
import discord
from discord.ext import commands
from discord import app_commands
from src.database import Database
from src.config import Config

logger = logging.getLogger('counting_game')

class CountingGame(commands.Cog):
    """Commands and logic for the counting game."""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.load()
        self.database = Database(self.config.database_path)
        self.current_count = 0
        self.target_number = random.randint(1, 100)
        self.last_counter = None
        self.counting_channel = None
        self.is_initialized = False
        self._load_game_state()
        
    async def initialize(self):
        """Initialize the counting game and announce presence."""
        if self.is_initialized:
            return
            
        try:
            self.counting_channel = self.bot.get_channel(self.config.counting_channel_id)
            if not self.counting_channel:
                logger.error(f"❌ Could not find counting channel: {self.config.counting_channel_id}")
                return

            # Announce bot presence and game state
            await self.counting_channel.send(
                "🎲 Counting game is ready!\n"
                f"Current count is at {self.current_count}\n"
                f"Next number needed: {self.current_count}"
            )
            logger.info(f"✅ Counting game initialized. Current count: {self.current_count}")
            self.is_initialized = True
        except Exception as e:
            logger.error(f"❌ Failed to initialize counting game: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Handle initialization when bot is ready."""
        await self.initialize()

    def _load_game_state(self):
        """Load game state from database."""
        state = self.database.get_game_state()
        if state:
            self.current_count, self.target_number, self.last_counter = state
        else:
            # Initialize game state
            self.current_count = 0
            self.target_number = random.randint(1, 100)
            self.last_counter = None
            self._save_game_state()

    def _save_game_state(self):
        """Save current game state to database."""
        self.database.save_game_state(
            self.current_count, 
            self.target_number, 
            self.last_counter
        )

    def _record_win(self, user_id):
        """Record a win for the user."""
        self.database.record_win(user_id)

    async def _show_leaderboard(self, channel):
        """Display the counting game leaderboard."""
        leaders = self.database.get_leaderboard()

        if not leaders:
            await channel.send("No winners yet!")
            return

        embed = discord.Embed(
            title="🦢 Silly Goose Leaderboard",
            color=discord.Color.gold()
        )

        for i, (user_id, wins) in enumerate(leaders, 1):
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"User {user_id}"
            embed.add_field(
                name=f"#{i} {name}",
                value=f"{wins} {'win' if wins == 1 else 'wins'}",
                inline=False
            )

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitor counting channel for numbers."""
        # Skip if wrong channel or bot message
        if (message.channel.id != self.config.counting_channel_id or 
            message.author.bot):
            return

        # Only process if message contains a number
        if not message.content.strip().isdigit():
            return

        number = int(message.content)
        
        if number != self.current_count:
            await message.channel.send(f"❌ Wrong number! We're at {self.current_count}, so the next number should be {self.current_count}!")
            return
            
        if message.author.id == self.last_counter:
            await message.channel.send("❌ Wait for someone else to go!")
            return

        # Valid number
        self.last_counter = message.author.id
        
        if number == self.target_number:
            self._record_win(message.author.id)
            await message.channel.send("🦢 HONK HONK! We have a winner!")
            await message.channel.send(f"Congratulations {message.author.mention}, you're today's Silly Goose! 🎉")
            await self._show_leaderboard(message.channel)
            
            self.current_count = 0
            self.target_number = random.randint(1, 100)
            self.last_counter = None
            await message.channel.send("New round starting! Begin at 0!")
        else:
            self.current_count += 1
            # Optional: React to confirm valid number
            await message.add_reaction("✅")
        
        self._save_game_state()

    @app_commands.command(name="counting_new", description="Start a new counting game")
    @app_commands.default_permissions(administrator=True)
    async def counting_new(self, interaction: discord.Interaction):
        """Start a new counting game."""
        self.current_count = 0
        self.target_number = random.randint(1, 100)
        self.last_counter = None
        self._save_game_state()
        
        await interaction.response.send_message(
            "🎲 New counting game started! Begin at 0!"
        )

    @app_commands.command(name="counting_leaderboard", description="Show the counting game leaderboard")
    async def counting_leaderboard(self, interaction: discord.Interaction):
        """Display the leaderboard."""
        await interaction.response.defer()
        await self._show_leaderboard(interaction.channel)

async def setup(bot):
    cog = CountingGame(bot)
    await bot.add_cog(cog)
    await cog.initialize()  # Initialize right after adding the cog
    logger.info("✅ Counting game cog loaded and initialized")
