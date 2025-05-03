import logging
import re
import json
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from . import utils
from .services import service_manager

# Constants for request handling
TIMEOUT = aiohttp.ClientTimeout(total=10)  # 10 second timeout
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds between retries

async def _make_request(url):
    """Make HTTP request with retry logic using shared session."""
    for attempt in range(MAX_RETRIES):
        try:
            if not service_manager.http_session:
                raise RuntimeError("HTTP session not initialized")
                
            async with service_manager.http_session.get(url, timeout=TIMEOUT) as response:
                return await response.text()
        except Exception as e:
            if attempt == MAX_RETRIES - 1:  # Last attempt
                logging.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts: {e}")
                raise
            await asyncio.sleep(RETRY_DELAY)  # Wait before retrying

async def fetchActivePlayer(url):
    """Fetch the active player ID from a BGA game URL."""
    try:
        r = await _make_request(url)
        pattern = re.compile(r'"active_player":"(\d+)"')
        result = pattern.search(r)
        if result:
            return int(result.group(1))
        return None
    except Exception as e:
        logging.error(f"Error fetching active player: {e}")
        return None

async def checkIfGameEnded(url):
    """Check if a BGA game has ended."""
    try:
        r = await _make_request(url)
        match = re.search(r"1°", r)
        return bool(match)
    except Exception as e:
        logging.error(f"Error checking if game ended: {e}")
        return False

async def getGameInfo(url):
    """Get game information from a BGA game URL."""
    try:
        r = await _make_request(url)
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
    try:
        r = await _make_request(url)
        soup = BeautifulSoup(r, 'html.parser')
        
        # Find the number of attendees from the HTML
        going_text = None
        going_elements = soup.find_all('p', class_='mantine-Text-root')
        for element in going_elements:
            if 'going' in element.text:
                going_text = element.text.strip()
                break

        going_count = 0
        if going_text:
            # Extract number from text like "9 going"
            try:
                going_count = int(''.join(filter(str.isdigit, going_text)))
            except ValueError:
                logging.warning(f"Could not parse going count from text: {going_text}")
        
        # Find the Remix context script for other event data
        scripts = soup.find_all('script')
        event_data = None
        
        for script in scripts:
            if script.string and 'window.__remixContext' in script.string:
                json_str = script.string.split('window.__remixContext = ')[1].split(';')[0]
                data = json.loads(json_str)
                
                # Debug log the raw data structure
                logging.debug(f"Raw event data: {data}")
                
                try:
                    event_data = data['state']['loaderData']['routes/events.$id']['event']
                except KeyError as e:
                    logging.error(f"Failed to extract event data, missing key: {e}")
                    logging.debug(f"Available keys: {data.keys()}")
                    return None
                break

        if not event_data:
            raise Exception("Could not find event data in page")

        # Extract data with fallbacks for missing fields
        event = {
            'url': url,
            'name': event_data.get('name', 'Unnamed Event'),
            'date': datetime.fromisoformat(event_data.get('startAt', datetime.now().isoformat()).replace('Z', '+00:00')),
            'venue': event_data.get('location', {}).get('name'),
            'address': ', '.join(filter(None, [
                event_data.get('location', {}).get('addressLine1'),
                event_data.get('location', {}).get('addressLine2'),
                event_data.get('location', {}).get('city'),
                event_data.get('location', {}).get('region'),
                event_data.get('location', {}).get('postalCode')
            ])) if event_data.get('location') else None,
            'going_count': going_count,  # Use parsed count from HTML
            'description': event_data.get('description', ''),
            'image_url': event_data.get('imageUrl')
        }
        return event

    except Exception as e:
        logging.error(f"Error scraping Aftergame event {url}: {str(e)}")
        logging.debug("Full error details:", exc_info=True)
        return None
