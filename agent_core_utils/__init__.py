
"""Agent Core Utilities - General-purpose utilities for agent applications."""

import sys
import os

# Add path for redis_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import agent_core_utils.redis_utils as redis_utils

# Import modules for re-export
from . import browser, location_tools, reasoning_tools, services

# Expose main service functions
from .services import initialize_llm_client, initialize_browser_driver, get_redis_client, get_redis_url

# Expose reasoning tools
from .reasoning_tools import analyze_text_with_llm, analyze_html_with_llm, extract_structured_data_with_llm

# Expose browser tools
from .browser import initialize_driver

# Explicit re-exports
__all__ = [
    # Modules
    "browser",
    "location_tools", 
    "reasoning_tools",
    "services",
    "redis_utils",
    # Service functions
    "initialize_llm_client",
    "initialize_browser_driver", 
    "get_redis_client",
    "get_redis_url",
    # Reasoning tools
    "analyze_text_with_llm",
    "analyze_html_with_llm", 
    "extract_structured_data_with_llm",
    # Browser tools
    "initialize_driver",
]

