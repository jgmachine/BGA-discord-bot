import sqlite3
from datetime import datetime
import logging
from .. import webscraper
from zoneinfo import ZoneInfo

def setup_events_table(conn):
    """Create the events table if it doesn't exist."""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS events (
            url TEXT PRIMARY KEY,
            name TEXT,
            date TIMESTAMP,
            venue TEXT,
            address TEXT,
            going_count INTEGER,
            description TEXT,
            image_url TEXT,
            last_updated TIMESTAMP
        )
    ''')
    conn.commit()

def add_event(conn, url):
    """Add a new event URL to track."""
    try:
        with conn:  # Use context manager for transaction
            setup_events_table(conn)
            conn.execute('INSERT OR IGNORE INTO events (url) VALUES (?)', (url,))
            return True
    except Exception as e:
        logging.error(f"Error adding event: {str(e)}")
        return False

def remove_event(conn, url):
    """Remove an event URL from tracking."""
    try:
        with conn:  # Use context manager for transaction
            conn.execute('DELETE FROM events WHERE url = ?', (url,))
            return True
    except Exception as e:
        logging.error(f"Error removing event: {str(e)}")
        return False

async def update_event(conn, url):
    """Update event data from Aftergame."""
    try:
        event = await webscraper.scrape_aftergame_event(url)
        if event:
            # Convert date to UTC for storage if it has timezone info
            event_date = event['date']
            if isinstance(event_date, datetime):
                if event_date.tzinfo is None:
                    # If no timezone, assume Pacific and convert to UTC
                    event_date = event_date.replace(tzinfo=ZoneInfo('America/Los_Angeles')).astimezone(ZoneInfo('UTC'))
                else:
                    # If has timezone, convert to UTC
                    event_date = event_date.astimezone(ZoneInfo('UTC'))

            with conn:
                conn.execute('''
                    UPDATE events 
                    SET name=?, date=?, venue=?, address=?, going_count=?, 
                        description=?, image_url=?, last_updated=?
                    WHERE url=?
                ''', (
                    event['name'], 
                    event_date.strftime('%Y-%m-%d %H:%M:%S'),  # Store as UTC string
                    event['venue'], 
                    event['address'],
                    event['going_count'], 
                    event['description'], 
                    event['image_url'],
                    datetime.now(ZoneInfo('UTC')), 
                    url
                ))
                return True
    except Exception as e:
        logging.error(f"Error updating event: {str(e)}")
    return False

async def update_all_events(conn):
    """Update data for all tracked events."""
    cursor = conn.execute('SELECT url FROM events')
    for (url,) in cursor.fetchall():
        await update_event(conn, url)

def _row_to_dict(row):
    """Convert a sqlite3.Row to a dictionary with proper datetime conversion."""
    if not row:
        return None
    data = {key: row[key] for key in row.keys()}
    # Convert string dates to datetime objects with proper timezone
    if 'date' in data and data['date']:
        try:
            # Parse as naive datetime first
            naive_dt = datetime.strptime(data['date'], '%Y-%m-%d %H:%M:%S')
            # Assign UTC timezone
            utc_dt = naive_dt.replace(tzinfo=ZoneInfo('UTC'))
            # Convert to Pacific time
            data['date'] = utc_dt.astimezone(ZoneInfo('America/Los_Angeles'))
        except (ValueError, TypeError):
            logging.error(f"Failed to parse date: {data['date']}")
            data['date'] = None
    return data

def get_next_event(conn):
    """Get the next upcoming event."""
    now = datetime.utcnow()
    cursor = conn.execute('''
        SELECT * FROM events 
        WHERE date > ? 
        ORDER BY date ASC 
        LIMIT 1
    ''', (now,))
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()
    return _row_to_dict(row)

def get_all_events(conn):
    """Get all tracked events."""
    cursor = conn.execute('SELECT * FROM events ORDER BY date ASC')
    cursor.row_factory = sqlite3.Row
    rows = cursor.fetchall()
    return [_row_to_dict(row) for row in rows]
