import logging
import re
import json
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from . import utils

# Constants for request handling
TIMEOUT = aiohttp.ClientTimeout(total=10)  # 10 second timeout
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds between retries

async def _make_request(url, session):
    """Make HTTP request with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            async with session.get(url, timeout=TIMEOUT) as response:
                return await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt == MAX_RETRIES - 1:  # Last attempt
                logging.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts: {e}")
                raise
            await asyncio.sleep(RETRY_DELAY)  # Wait before retrying

async def fetchActivePlayer(url):
    """Fetch the active player ID from a BGA game URL."""
    async with aiohttp.ClientSession() as session:
        try:
            r = await _make_request(url, session)
            pattern = re.compile(r'"active_player":"(\d+)"')
            result = pattern.search(r)
            if result:
                active_player_value = result.group(1)
                return int(active_player_value)
            return None
        except Exception as e:
            logging.error(f"Error fetching active player: {e}")
            return None

async def checkIfGameEnded(url):
    """Check if a BGA game has ended."""
    async with aiohttp.ClientSession() as session:
        try:
            r = await _make_request(url, session)
            match = re.search(r"1°", r)
            return bool(match)
        except Exception as e:
            logging.error(f"Error checking if game ended: {e}")
            return False

async def getGameInfo(url):
    """Get game information from a BGA game URL."""
    async with aiohttp.ClientSession() as session:
        try:
            r = await _make_request(url, session)
            gameName = re.search(r'completesetup\([^,]+,\s*("[^"]+")', r)
            activePlayerIdPattern = re.compile(r'"active_player":"(\d+)"')
            resultActivePlayerId = activePlayerIdPattern.search(r)

            if gameName and resultActivePlayerId:
                gameTitle = gameName.group(1)
                convertedGameTitle = utils.convertHtmlEntitiesToCharacters(gameTitle)
                activePlayerId = resultActivePlayerId.group(1)
                logging.info(
                    f"Found game title: {convertedGameTitle} \nFound active player: {activePlayerId}"
                )
                return convertedGameTitle, activePlayerId
            logging.error("Failed to fetch game info - patterns not found in response")
            return None
        except Exception as e:
            logging.error(f"Error getting game info: {e}")
            return None

async def scrape_aftergame_event(url):
    """Scrape event information from an Aftergame event URL."""
    async with aiohttp.ClientSession() as session:
        try:
            r = await _make_request(url, session)
            soup = BeautifulSoup(r, 'html.parser')
            
            # Find the Remix context script
            scripts = soup.find_all('script')
            event_data = None
            
            for script in scripts:
                if script.string and 'window.__remixContext' in script.string:
                    json_str = script.string.split('window.__remixContext = ')[1].split(';')[0]
                    data = json.loads(json_str)
                    event_data = data['state']['loaderData']['routes/events.$id']['event']
                    break

            if not event_data:
                raise Exception("Could not find event data in page")

            event = {
                'url': url,
                'name': event_data['name'],
                'date': datetime.fromisoformat(event_data['startAt'].replace('Z', '+00:00')),
                'venue': event_data['location']['name'] if event_data['location'] else None,
                'address': ', '.join(filter(None, [
                    event_data['location'].get('addressLine1'),
                    event_data['location'].get('addressLine2'),
                    event_data['location'].get('city'),
                    event_data['location'].get('region'),
                    event_data['location'].get('postalCode')
                ])) if event_data['location'] else None,
                'going_count': event_data['playersCount'],
                'description': event_data['description'],
                'image_url': event_data['imageUrl']
            }
            return event

        except Exception as e:
            logging.error(f"Error scraping Aftergame event {url}: {str(e)}")
            return None
