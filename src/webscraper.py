import logging
import requests
import re
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
