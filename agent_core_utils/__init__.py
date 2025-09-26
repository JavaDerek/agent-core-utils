
"""Agent Core Utilities - General-purpose utilities for agent applications."""

import sys
import os

# Add path for redis_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import agent_core_utils.redis_utils as redis_utils

# Import modules for re-export
from . import browser, location_tools, reasoning_tools, services

# Import new agent communication modules
from . import protocols, config, redis_streams, state_persistence, delegation

# Expose main service functions
from .services import initialize_llm_client, initialize_browser_driver, get_redis_client, get_redis_url

# Expose reasoning tools
from .reasoning_tools import analyze_text_with_llm, analyze_html_with_llm, extract_structured_data_with_llm

# Expose agent communication classes
from .protocols import DelegationTask, TaskResponse, TaskError, TaskProgress
from .config import CommunicationConfig
from .redis_streams import RedisStreamManager
from .state_persistence import AgentStateManager
from .delegation import AgentDelegator, AgentDelegate

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
    "protocols",
    "config",
    "redis_streams",
    "state_persistence",
    "delegation",
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
    # Agent communication classes
    "DelegationTask",
    "TaskResponse", 
    "TaskError",
    "TaskProgress",
    "CommunicationConfig",
    "RedisStreamManager",
    "AgentStateManager",
    "AgentDelegator",
    "AgentDelegate",
]

