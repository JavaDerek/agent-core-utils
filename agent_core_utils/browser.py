"""Browser utilities for agent applications."""

from .services import initialize_browser_driver

def initialize_driver():
    """Initialize a browser driver.
    
    This forwards to the main services module for consistent browser setup.
    """
    return initialize_browser_driver()
