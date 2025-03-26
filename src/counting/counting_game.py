import logging
import random
import discord
from discord.ext import commands
from discord import app_commands
from src.database import Database
from src.config import Config
from pathlib import Path

logger = logging.getLogger('counting_game')

class CountingGame(commands.Cog):
    """Commands and logic for the counting game."""
    
    # Class constant for target number range
    TARGET_RANGE = (1, 10)  # Easier for testing - change to (1, 100) for production
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.load()
        self.database = Database(self.config.database_path)
        
        # Initialize database tables immediately
        logger.info("Creating database tables...")
        with self.database.transaction():
            self.database.create_tables()
        
        self.current_count = 0
        self.target_number = None
        self.last_counter = None
        self.counting_channel = None
        self.ready = False
        self._load_game_state()
        logger.info(f"CountingGame initialized with channel ID: {self.config.counting_channel_id}")

    def _get_random_spawn_gif(self) -> str:
        """Get a random GIF URL from the spawn-gifs.txt file."""
        gif_file = Path(__file__).parent.parent / "gifs" / "spawn-gifs.txt"
        with open(gif_file, 'r') as f:
            gifs = [line.strip() for line in f if line.strip()]
        return random.choice(gifs)

    def _get_random_goose_gif(self) -> str:
        """Get a random GIF URL from the goose-gifs.txt file."""
        gif_file = Path(__file__).parent.parent / "gifs" / "goose-gifs.txt"
        with open(gif_file, 'r') as f:
            gifs = [line.strip() for line in f if line.strip()]
        return random.choice(gifs)

    def _get_random_negative_emoji(self) -> str:
        """Get a random negative emoji."""
        negative_emojis = ['❌', '😢', '😭', '😔', '😪', '💔', '🤦', '😑', '😓', '🙅']
        return random.choice(negative_emojis)

    async def announce_game_status(self):
        """Announce game status in counting channel."""
        if not self.counting_channel:
            self.counting_channel = self.bot.get_channel(self.config.counting_channel_id)
            if not self.counting_channel:
                logger.error("❌ Could not find counting channel")
                return False
                
        try:
            await self.counting_channel.send(self._get_random_spawn_gif())
            await self.counting_channel.send(
                f"Last number counted: `{self.current_count}`"
            )
            logger.info("✅ Game status announced successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to announce game status: {e}")
            return False

    @commands.Cog.listener()
    async def on_ready(self):
        """Handle initialization when bot is ready."""
        if self.ready:  # Avoid duplicate initialization
            return
            
        try:
            logger.info("🔄 Starting counting game initialization...")
            
            logger.info("Finding counting channel...")
            self.counting_channel = self.bot.get_channel(self.config.counting_channel_id)
            if not self.counting_channel:
                logger.error(f"❌ Could not find counting channel with ID: {self.config.counting_channel_id}")
                return

            # Force reload game state after ensuring tables exist
            logger.info("Loading game state...")
            self._load_game_state()
            self.ready = True
            
            logger.info("Sending startup message...")
            try:
                await self.counting_channel.send(
                    f"🎲 **Counting Game is Ready!**\n"
                    f"Current count: `{self.current_count}`\n"
                    f"{self._get_random_spawn_gif()}"
                )
                logger.info("✅ Counting game startup complete!")
            except Exception as e:
                logger.error(f"Failed to send startup message: {e}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize counting game: {e}", exc_info=True)
            self.ready = False

    def _generate_target(self):
        """Generate a new target number using the configured range."""
        return random.randint(*self.TARGET_RANGE)

    def _load_game_state(self):
        """Load game state from database."""
        state = self.database.get_game_state()
        if (state):
            self.current_count, self.target_number, self.last_counter = state
        else:
            # Initialize game state
            self.current_count = 0
            self.target_number = self._generate_target()
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

    def _get_rank_info(self, wins):
        """Get title and color based on win count."""
        ranks = [
            (100, "🔱 Legendary Goose", discord.Color.gold()),
            (50, "👑 Royal Goose", discord.Color.purple()),
            (25, "⚔️ Veteran Goose", discord.Color.blue()),
            (10, "🎖️ Elite Goose", discord.Color.green()),
            (0, "🥚 Gosling", discord.Color.light_grey())
        ]
        for threshold, title, color in ranks:
            if wins >= threshold:
                return title, color
        return "🥚 Gosling", discord.Color.light_grey()

    def _create_progress_bar(self, wins, max_wins=20):
        """Create a visual progress bar using block elements."""
        progress = min(wins / max_wins, 1.0)
        bar_length = 10
        filled = int(bar_length * progress)
        empty = bar_length - filled
        return "█" * filled + "░" * empty

    async def _show_leaderboard(self, channel):
        """Create and return the leaderboard embed."""
        leaders = self.database.get_leaderboard()

        if not leaders:
            return "No winners yet!"

        total_games = sum(wins for _, wins in leaders)
        top_title, top_color = self._get_rank_info(leaders[0][1] if leaders else 0)

        embed = discord.Embed(
            title="🦢 Silly Goose Championship Board",
            description=f"Total Games Played: {total_games}\nCurrent Champion: {top_title}",
            color=top_color
        )

        # Medal emojis for top 3
        medals = ["🥇", "🥈", "🥉"]

        for i, (user_id, wins) in enumerate(leaders, 1):
            try:
                user = await self.bot.fetch_user(user_id)
                name = user.name if user else f"Unknown User ({user_id})"
            except discord.NotFound:
                name = f"Unknown User ({user_id})"

            title, _ = self._get_rank_info(wins)
            progress_bar = self._create_progress_bar(wins)
            
            # Format position with medal if in top 3
            position = f"{medals[i-1]} " if i <= 3 else f"#{i} "
            
            # Special formatting for current winner
            if i == 1:
                name = f"👑 {name} 👑"

            value = (
                f"**{title}**\n"
                f"`{progress_bar}` {wins} {'win' if wins == 1 else 'wins'}\n"
                f"{'🔥 On Fire!' if wins >= 3 else ''}"
            )
            
            embed.add_field(
                name=f"{position}{name}",
                value=value,
                inline=False
            )

        embed.set_footer(text="🎯 Target: Get the most wins to become the Legendary Goose!")
        return embed

    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitor counting channel for numbers."""
        if (message.channel.id != self.config.counting_channel_id or 
            message.author.bot):
            return

        if not message.content.strip().isdigit():
            return

        number = int(message.content)
        expected_number = self.current_count + 1
        
        if number != expected_number:
            await message.add_reaction(self._get_random_negative_emoji())
            await message.channel.send(f"❌ Wrong number! The last number counted was {self.current_count}.")
            return
            
        if message.author.id == self.last_counter:
            await message.add_reaction(self._get_random_negative_emoji())
            await message.channel.send(f"❌ Wait your turn!.")
            return

        self.last_counter = message.author.id
        self.current_count = number
        
        if number == self.target_number:
            self._record_win(message.author.id)
            await message.channel.send(self._get_random_goose_gif())
            await message.channel.send("🦢 HONK HONK! We have a winner!")
            await message.channel.send(f"Congratulations {message.author.mention}, you are now the holder of the Silly Goose! 🎉")
            
            leaderboard = await self._show_leaderboard(message.channel)
            await message.channel.send(
                content="" if isinstance(leaderboard, discord.Embed) else leaderboard,
                embed=leaderboard if isinstance(leaderboard, discord.Embed) else None
            )
            
            self.current_count = -1
            self.target_number = self._generate_target()
            self.last_counter = None
            await message.channel.send("New round starting! I'm a computer, so start at 0!")
        else:
            await message.add_reaction("✅")
        
        self._save_game_state()

    @app_commands.command(name="counting_new", description="Start a new counting game")        
    @app_commands.default_permissions(administrator=True)
    async def counting_new(self, interaction: discord.Interaction):
        """Start a new counting game."""
        self.current_count = 0
        self.target_number = self._generate_target()
        self.last_counter = None
        self._save_game_state()
        await interaction.response.send_message(
            "🎲 New counting game started! Begin at 0!"
        )

    @app_commands.command(name="counting_leaderboard", description="Show the counting game leaderboard")
    async def counting_leaderboard(self, interaction: discord.Interaction):
        """Display the leaderboard."""
        await interaction.response.defer()
        leaderboard = await self._show_leaderboard(interaction.channel)
        await interaction.followup.send(
            content="" if isinstance(leaderboard, discord.Embed) else leaderboard,
            embed=leaderboard if isinstance(leaderboard, discord.Embed) else None
        )

async def setup(bot):
    await bot.add_cog(CountingGame(bot))
    logger.info("✅ Counting game cog loaded")
