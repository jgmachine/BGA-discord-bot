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
        setup_events_table(conn)
        conn.execute('INSERT OR IGNORE INTO events (url) VALUES (?)', (url,))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error adding event: {str(e)}")
        return False

def remove_event(conn, url):
    """Remove an event URL from tracking."""
    try:
        conn.execute('DELETE FROM events WHERE url = ?', (url,))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error removing event: {str(e)}")
        return False

async def update_event(conn, url):
    """Update event data from Aftergame."""
    try:
        event = await webscraper.scrape_aftergame_event(url)
        if event:
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
            conn.commit()
            return True
    except Exception as e:
        logging.error(f"Error updating event: {str(e)}")
    return False

async def update_all_events(conn):
    """Update data for all tracked events."""
    cursor = conn.execute('SELECT url FROM events')
    for (url,) in cursor.fetchall():
        await update_event(conn, url)

def get_next_event(conn):
    """Get the next upcoming event."""
    now = datetime.utcnow()
    cursor = conn.execute('''
        SELECT * FROM events 
        WHERE date > ? 
        ORDER BY date ASC 
        LIMIT 1
    ''', (now,))
    return cursor.fetchone()

def get_all_events(conn):
    """Get all tracked events."""
    cursor = conn.execute('SELECT * FROM events ORDER BY date ASC')
    return cursor.fetchall()
