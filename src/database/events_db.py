import sqlite3
from datetime import datetime
import logging
from .. import webscraper

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
            with conn:  # Use context manager for transaction
                conn.execute('''
                    UPDATE events 
                    SET name=?, date=?, venue=?, address=?, going_count=?, 
                        description=?, image_url=?, last_updated=?
                    WHERE url=?
                ''', (
                    event['name'], event['date'], event['venue'], event['address'],
                    event['going_count'], event['description'], event['image_url'],
                    datetime.utcnow(), url
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
    data = dict(zip([col[0] for col in row.description], row))
    # Convert string dates back to datetime objects
    if 'date' in data and isinstance(data['date'], str):
        data['date'] = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
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
