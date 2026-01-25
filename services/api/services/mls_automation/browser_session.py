"""
Browser session manager for MLS automation.
Tracks active browser sessions per listing.
"""
from typing import Dict, Optional, Tuple
from uuid import UUID
from threading import Lock

try:
    from playwright.async_api import Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = None
    BrowserContext = None
    Page = None


class BrowserSession:
    """Represents an active browser session for a listing."""
    def __init__(self, listing_id: UUID, browser: Browser, context: BrowserContext, page: Page):
        self.listing_id = listing_id
        self.browser = browser
        self.context = context
        self.page = page
        self.is_active = True


# Global session storage: listing_id -> BrowserSession
_active_sessions: Dict[UUID, BrowserSession] = {}
_session_lock = Lock()


def get_session(listing_id: UUID) -> Optional[BrowserSession]:
    """
    Get active browser session for a listing.
    
    Args:
        listing_id: The listing ID
        
    Returns:
        BrowserSession if exists and active, None otherwise
    """
    with _session_lock:
        session = _active_sessions.get(listing_id)
        if session and session.is_active:
            return session
        # Clean up inactive sessions
        if session:
            del _active_sessions[listing_id]
        return None


def set_session(listing_id: UUID, session: BrowserSession) -> None:
    """
    Store browser session for a listing.
    
    Args:
        listing_id: The listing ID
        session: BrowserSession to store
    """
    with _session_lock:
        _active_sessions[listing_id] = session


def close_session(listing_id: UUID) -> bool:
    """
    Close and remove browser session for a listing.
    
    Args:
        listing_id: The listing ID
        
    Returns:
        True if session was found and closed, False otherwise
    """
    from services.api.services.mls_automation.automation_service import _playwright_instances
    
    with _session_lock:
        session = _active_sessions.get(listing_id)
        if not session:
            return False
        
        try:
            session.is_active = False
            # Note: browser.close() needs to be called from async context
            # This function should be converted to async or handled differently
            session.browser.close()
            # Stop playwright instance
            if listing_id in _playwright_instances:
                _playwright_instances[listing_id].stop()
                del _playwright_instances[listing_id]
        except Exception:
            pass  # Browser might already be closed
        
        del _active_sessions[listing_id]
        return True


def is_session_active(listing_id: UUID) -> bool:
    """
    Check if an active browser session exists for a listing.
    
    Args:
        listing_id: The listing ID
        
    Returns:
        True if active session exists, False otherwise
    """
    return get_session(listing_id) is not None
