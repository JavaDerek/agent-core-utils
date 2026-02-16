import logging
import os
from pathlib import Path

import redis.asyncio as redis
import requests
from langchain_openai import ChatOpenAI
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def _reset_redis_client_for_testing() -> None:
    """Reset the Redis client for testing purposes only."""
    global _redis_client
    _redis_client = None


def get_redis_client() -> redis.Redis:
    """Return a Redis client, initializing it on first use."""
    global _redis_client
    if _redis_client is None:
        host = os.environ.get("REDIS_HOST", "localhost")
        port = int(os.environ.get("REDIS_PORT", "6379"))
        db = int(os.environ.get("REDIS_DB", "0"))
        username = os.environ.get("REDIS_USERNAME", "default")
        password = os.environ.get("REDIS_PASSWORD")
        _redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            username=username,
            password=password,
        )
    return _redis_client


def get_redis_url() -> str | None:
    """Return a redis connection URL built from environment settings."""
    url = os.environ.get("REDIS_URL")
    if url:
        return url

    host = os.environ.get("REDIS_HOST")
    if not host:
        return None

    port = os.environ.get("REDIS_PORT", "6379")
    db = os.environ.get("REDIS_DB", "0")
    username = os.environ.get("REDIS_USERNAME")
    password = os.environ.get("REDIS_PASSWORD")

    auth = ""
    if username or password:
        user = username or ""
        pass_part = f":{password}" if password else ""
        auth = f"{user}{pass_part}@"

    return f"redis://{auth}{host}:{port}/{db}"


def _import_langfuse_handler(public_key: str, secret_key: str, host: str):
    """Import and create a Langfuse CallbackHandler.

    Separated for testability — callers can mock this to simulate ImportError.
    """
    from langfuse.callback import CallbackHandler  # type: ignore

    return CallbackHandler(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
    )


def _get_langfuse_callbacks() -> list:
    """Return Langfuse LangChain callbacks if env vars are configured.

    Reads LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, and LANGFUSE_HOST from
    environment.  Returns ``[CallbackHandler(...)]`` when both keys are
    present, or ``[]`` otherwise.  Gracefully degrades if the ``langfuse``
    package is not installed.
    """
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    if not public_key or not secret_key:
        return []

    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
    try:
        handler = _import_langfuse_handler(public_key, secret_key, host)
        logger.info("Langfuse LangChain callbacks enabled (host=%s)", host)
        return [handler]
    except ImportError:
        logger.warning("langfuse package not installed — LLM callbacks disabled")
        return []
    except Exception:
        logger.exception("Failed to create Langfuse callback handler")
        return []


def initialize_llm_client() -> ChatOpenAI:
    """
    Initialize and return a reusable ChatOpenAI client based on environment configuration.

    Environment variables used:
    - LLM_MODEL: Model name (default: "llama3.1:8b")
    - LLM_BASE_URL: Base URL for the LLM service
    - LLM_API_KEY: API key for authentication (default: "ollama")
    - LLM_TEMPERATURE: Temperature setting (default: 0.1)
    - LLM_DISABLE_TEMPERATURE: Set to "1", "true", or "yes" to disable temperature
    - LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY: Auto-wire Langfuse tracing callbacks
    """
    logger.info("Initializing LLM client")

    # Get configuration from environment with sensible defaults
    model = os.environ.get("LLM_MODEL", "llama3.1:8b")
    base_url = os.environ.get("LLM_BASE_URL")
    api_key = os.environ.get("LLM_API_KEY", "ollama")

    # Handle temperature configuration
    disable_temp = os.environ.get("LLM_DISABLE_TEMPERATURE", "").lower() in {"1", "true", "yes"}
    temperature = os.environ.get("LLM_TEMPERATURE", "0.1")

    kwargs = {
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
    }

    if not disable_temp:
        kwargs["temperature"] = float(temperature)

    callbacks = _get_langfuse_callbacks()
    if callbacks:
        kwargs["callbacks"] = callbacks

    return ChatOpenAI(**kwargs)


def initialize_browser_driver():
    """
    Initialize and return a reusable Selenium WebDriver instance with suppressed logging.
    
    Returns a Chrome WebDriver in headless mode with optimized settings for automation.
    Falls back to a dummy driver that uses requests if Chrome setup fails.
    """
    logger.info("Initializing headless browser driver")

    # Chrome Options - configure browser behavior
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1200")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    
    # Suppress logging to reduce console noise
    options.add_argument('--log-level=3') 
    options.add_argument("--mute-audio")
    options.add_experimental_option(
        'excludeSwitches', ['enable-logging', 'enable-automation']
    )
    
    # ChromeDriver Service - attempt to download ChromeDriver, fall back to system binary
    try:
        driver_path = ChromeDriverManager().install()
    except Exception:
        driver_path = "/usr/bin/chromedriver"

    service = ChromeService(driver_path, log_output=os.devnull)

    try:
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception:
        # Fallback dummy driver that uses requests for basic functionality
        class DummyDriver:
            def __init__(self):
                self.page_source = ""

            def get(self, url: str) -> None:
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0 Safari/537.36"
                    )
                }
                response = requests.get(url, timeout=10, headers=headers)
                self.page_source = response.text

            def save_screenshot(self, path: str) -> bool:
                Path(path).write_bytes(b"dummy")
                return True

            def quit(self) -> None:
                pass

        return DummyDriver()
