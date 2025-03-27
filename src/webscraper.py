import logging
import requests
import re
import json
from bs4 import BeautifulSoup
from datetime import datetime
from . import utils


async def fetchActivePlayer(url):
    r = requests.get(url).text

    pattern = re.compile(r'"active_player":"(\d+)"')
    result = pattern.search(r)

    if result:
        active_player_value = result.group(1)
        return int(active_player_value)


async def checkIfGameEnded(url):
    r = requests.get(url).text
    # Checking if 1° is in the text, this occurs when a list of results is avaiable
    match = re.search(r"1°", r)

    if match:
        return True
    else:
        return False


async def getGameInfo(url):
    r = requests.get(url).text

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
    else:
        logging.error(
            f"Failed to fetch game info:\nGame name: {gameName}\nActive Player Id: {resultActivePlayerId}"
        )


async def scrape_aftergame_event(url):
    """Scrape event information from an Aftergame event URL."""
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the Remix context script that contains event data
        scripts = soup.find_all('script')
        event_data = None
        
        for script in scripts:
            if script.string and 'window.__remixContext' in script.string:
                # Extract JSON data from script
                json_str = script.string.split('window.__remixContext = ')[1].split(';')[0]
                data = json.loads(json_str)
                event_data = data['state']['loaderData']['routes/events.$id']['event']
                break

        if not event_data:
            raise Exception("Could not find event data in page")

        # Extract relevant information
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
