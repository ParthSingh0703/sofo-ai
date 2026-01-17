"""
Enhanced login detection and handling for MLS automation.
Supports multiple detection strategies and robust timeout handling.
"""
import time
from typing import Optional, Dict, Any, Callable
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError


def detect_login_state(page: Page, timeout: float = 5.0) -> bool:
    """
    Detect if user is already logged in using multiple strategies.
    
    Checks multiple indicators:
    1. Create/Add Listing buttons
    2. User avatar/profile indicators
    3. Logout button presence
    4. Absence of login form elements
    5. Session storage / cookies
    6. User menu/account indicators
    
    Args:
        page: Playwright page object
        timeout: Maximum time to wait for elements (seconds)
        
    Returns:
        True if logged in, False otherwise
    """
    strategies = [
        _check_listing_buttons,
        _check_user_indicators,
        _check_logout_button,
        _check_no_login_form,
        _check_session_data,
        _check_user_menu
    ]
    
    # Use any strategy that returns True (any positive indicator)
    for strategy in strategies:
        try:
            if strategy(page, timeout):
                return True
        except Exception:
            continue
    
    return False


def wait_for_manual_login(
    page: Page,
    timeout: int = 300,
    poll_interval: float = 2.0,
    progress_callback: Optional[Callable[[float, bool], None]] = None
) -> bool:
    """
    Wait for user to manually log in with enhanced monitoring.
    
    Monitors multiple indicators and provides progress feedback.
    
    Args:
        page: Playwright page object
        timeout: Maximum time to wait (seconds, default 5 minutes)
        poll_interval: Time between checks (seconds)
        progress_callback: Optional callback(seconds_elapsed, is_logged_in)
        
    Returns:
        True if login detected, False if timeout
        
    Raises:
        TimeoutError: If timeout exceeded
    """
    start_time = time.time()
    last_url = page.url
    
    while time.time() - start_time < timeout:
        elapsed = time.time() - start_time
        
        # Check if URL changed (might indicate login redirect)
        current_url = page.url
        if current_url != last_url:
            # URL changed, wait a moment then check login state
            time.sleep(1.0)
            if detect_login_state(page, timeout=3.0):
                if progress_callback:
                    progress_callback(elapsed, True)
                return True
            last_url = current_url
        
        # Check login state
        if detect_login_state(page, timeout=2.0):
            if progress_callback:
                progress_callback(elapsed, True)
            return True
        
        # Progress callback
        if progress_callback:
            progress_callback(elapsed, False)
        
        time.sleep(poll_interval)
    
    raise TimeoutError(f"Timeout waiting for manual login after {timeout} seconds")


def _check_listing_buttons(page: Page, timeout: float) -> bool:
    """Check for Create/Add Listing buttons."""
    try:
        create_patterns = [
            'button:has-text("Create Listing")',
            'button:has-text("Add Listing")',
            'button:has-text("New Listing")',
            'a:has-text("Create Listing")',
            'a:has-text("Add Listing")',
            '[role="button"]:has-text("Create Listing")',
            'text=/Create.*Listing|Add.*Listing|New.*Listing/i'
        ]
        
        for pattern in create_patterns:
            try:
                locator = page.locator(pattern).first
                if locator.count() > 0 and locator.is_visible(timeout=timeout * 1000):
                    return True
            except:
                continue
        return False
    except:
        return False


def _check_user_indicators(page: Page, timeout: float) -> bool:
    """Check for user avatar/profile indicators."""
    try:
        avatar_patterns = [
            '[alt*="avatar" i]',
            '[alt*="user" i]',
            '[alt*="profile" i]',
            '[class*="avatar" i]',
            '[class*="user-profile" i]',
            '[class*="profile-picture" i]',
            '[id*="avatar" i]',
            '[id*="user-profile" i]'
        ]
        
        for pattern in avatar_patterns:
            try:
                locator = page.locator(pattern).first
                if locator.count() > 0 and locator.is_visible(timeout=timeout * 1000):
                    return True
            except:
                continue
        return False
    except:
        return False


def _check_logout_button(page: Page, timeout: float) -> bool:
    """Check for logout button/menu."""
    try:
        logout_patterns = [
            'button:has-text("Logout")',
            'button:has-text("Log out")',
            'button:has-text("Sign out")',
            'a:has-text("Logout")',
            'a:has-text("Log out")',
            '[role="button"]:has-text("Logout")',
            'text=/Log.*out|Sign.*out/i'
        ]
        
        for pattern in logout_patterns:
            try:
                locator = page.locator(pattern).first
                if locator.count() > 0 and locator.is_visible(timeout=timeout * 1000):
                    return True
            except:
                continue
        return False
    except:
        return False


def _check_no_login_form(page: Page, timeout: float) -> bool:
    """Check absence of login form elements."""
    try:
        login_indicators = [
            'form:has(input[type="password"])',
            'form:has([name*="password" i])',
            'input[type="password"]',
            'input[name*="password" i]',
            'button:has-text("Login")',
            'button:has-text("Sign in")',
            'text=/Login|Sign.*in/i:near(input[type="password"])'
        ]
        
        # If we find NO login indicators, we're likely logged in
        for pattern in login_indicators:
            try:
                locator = page.locator(pattern).first
                if locator.count() > 0:
                    return False  # Login form present
            except:
                continue
        
        # No login form found - might be logged in
        # But this is weak evidence, so return False to require other indicators
        return False
    except:
        return False


def _check_session_data(page: Page, timeout: float) -> bool:
    """Check for session storage or cookies indicating login."""
    try:
        # Check sessionStorage for common keys
        session_keys = page.evaluate("""
            () => {
                const keys = [];
                for (let i = 0; i < sessionStorage.length; i++) {
                    keys.push(sessionStorage.key(i));
                }
                return keys;
            }
        """)
        
        login_indicators = ['token', 'auth', 'user', 'session', 'logged', 'authenticated']
        if any(key.lower() for key in session_keys if any(ind in key.lower() for ind in login_indicators)):
            return True
        
        # Check localStorage
        local_keys = page.evaluate("""
            () => {
                const keys = [];
                for (let i = 0; i < localStorage.length; i++) {
                    keys.push(localStorage.key(i));
                }
                return keys;
            }
        """)
        
        if any(key.lower() for key in local_keys if any(ind in key.lower() for ind in login_indicators)):
            return True
        
        # Check cookies
        cookies = page.context.cookies()
        cookie_names = [c.get('name', '').lower() for c in cookies]
        if any(ind in name for name in cookie_names for ind in login_indicators):
            return True
        
        return False
    except:
        return False


def _check_user_menu(page: Page, timeout: float) -> bool:
    """Check for user menu/dropdown."""
    try:
        menu_patterns = [
            '[class*="user-menu" i]',
            '[class*="account-menu" i]',
            '[id*="user-menu" i]',
            '[id*="account-menu" i]',
            '[aria-label*="user menu" i]',
            '[aria-label*="account menu" i]'
        ]
        
        for pattern in menu_patterns:
            try:
                locator = page.locator(pattern).first
                if locator.count() > 0 and locator.is_visible(timeout=timeout * 1000):
                    return True
            except:
                continue
        return False
    except:
        return False
