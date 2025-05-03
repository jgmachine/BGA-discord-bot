import aiohttp
import logging
from typing import Optional

class ServiceManager:
    """Central manager for shared services and resources."""
    
    def __init__(self):
        self.http_session: Optional[aiohttp.ClientSession] = None
        
    async def init(self):
        """Initialize services."""
        if not self.http_session:
            self.http_session = aiohttp.ClientSession()
        logging.info("✅ Service manager initialized")
        
    async def cleanup(self):
        """Cleanup services."""
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
        logging.info("✅ Service manager cleaned up")

# Global service manager instance
service_manager = ServiceManager()
