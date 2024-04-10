import re
import html


# Function to extract the game ID from a URL
def extractGameId(url):
    match = re.search(r"table=(\d+)", url)
    if match:
        return match.group(1)
    return None


def convertHtmlEntitiesToCharacters(inputString):
    # Check if the string contains any HTML entities
    if "&" in inputString:
        # Convert HTML entities to characters
        return html.unescape(inputString)
    else:
        # No HTML entities found, return the original string
        return inputString
