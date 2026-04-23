from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from .config import DEFAULT_CONFIG_PATH, CalendarConfig, load_config
from .renderer import render_month

logger = logging.getLogger(__name__)


class CommunityCalendar(commands.Cog):
    """Slash commands for rendering the local community event calendar."""

    def __init__(self, bot: commands.Bot, cfg: CalendarConfig):
        self.bot = bot
        self.cfg = cfg

    @app_commands.command(
        name="calendar",
        description="Show this month's local community events as an image.",
    )
    @app_commands.describe(
        month="Month number 1-12 (defaults to current month)",
        year="4-digit year (defaults to current year)",
    )
    async def calendar(
        self,
        interaction: discord.Interaction,
        month: Optional[int] = None,
        year: Optional[int] = None,
    ):
        await interaction.response.defer(thinking=True)

        now = datetime.now(self.cfg.tz)
        y = year if year is not None else now.year
        m = month if month is not None else now.month

        if not (1 <= m <= 12):
            await interaction.followup.send(
                "Month must be between 1 and 12.", ephemeral=True
            )
            return
        if not (1970 <= y <= 2100):
            await interaction.followup.send(
                "Year must be between 1970 and 2100.", ephemeral=True
            )
            return

        try:
            png = render_month(self.cfg, y, m, today=now.date())
        except Exception:
            logger.exception("Failed to render community calendar")
            await interaction.followup.send(
                "Something went wrong rendering the calendar.", ephemeral=True
            )
            return

        file = discord.File(io.BytesIO(png), filename=f"calendar-{y}-{m:02d}.png")
        await interaction.followup.send(file=file)


async def setup(bot: commands.Bot):
    cfg = load_config(DEFAULT_CONFIG_PATH)
    await bot.add_cog(CommunityCalendar(bot, cfg))
    logger.info("✅ Community calendar cog loaded")
