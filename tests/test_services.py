"""Tests for agent_core_utils.services module."""

import os
from unittest.mock import Mock, patch
import pytest
from agent_core_utils.services import (
    initialize_llm_client,
    initialize_browser_driver,
    get_redis_client,
    get_redis_url,
    _reset_redis_client_for_testing,
)


@pytest.fixture(autouse=True)
def reset_redis_client():
    """Reset the global Redis client before each test."""
    _reset_redis_client_for_testing()
    yield
    _reset_redis_client_for_testing()


class TestInitializeLLMClient:
    """Tests for initialize_llm_client function."""

    def test_initialize_llm_client_default_config(self, monkeypatch):
        """Test LLM client initialization with default configuration."""
        # Clear environment variables to test defaults
        monkeypatch.delenv("LLM_MODEL", raising=False)
        monkeypatch.delenv("LLM_BASE_URL", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.delenv("LLM_TEMPERATURE", raising=False)
        monkeypatch.delenv("LLM_DISABLE_TEMPERATURE", raising=False)
        
        with patch("agent_core_utils.services.ChatOpenAI") as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            result = initialize_llm_client()
            
            assert result == mock_client
            mock_openai.assert_called_once_with(
                model="llama3.1:8b",
                base_url=None,
                api_key="ollama",
                temperature=0.1
            )

    def test_initialize_llm_client_custom_config(self, monkeypatch):
        """Test LLM client initialization with custom configuration."""
        monkeypatch.setenv("LLM_MODEL", "custom-model")
        monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434")
        monkeypatch.setenv("LLM_API_KEY", "custom-key")
        monkeypatch.setenv("LLM_TEMPERATURE", "0.7")
        
        with patch("agent_core_utils.services.ChatOpenAI") as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            result = initialize_llm_client()
            
            assert result == mock_client
            mock_openai.assert_called_once_with(
                model="custom-model",
                base_url="http://localhost:11434",
                api_key="custom-key",
                temperature=0.7
            )

    def test_initialize_llm_client_disabled_temperature(self, monkeypatch):
        """Test LLM client initialization with temperature disabled."""
        monkeypatch.setenv("LLM_DISABLE_TEMPERATURE", "true")
        
        with patch("agent_core_utils.services.ChatOpenAI") as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            result = initialize_llm_client()
            
            assert result == mock_client
            # Should not include temperature when disabled
            expected_kwargs = {
                "model": "llama3.1:8b",
                "base_url": None,
                "api_key": "ollama",
            }
            mock_openai.assert_called_once_with(**expected_kwargs)


class TestInitializeBrowserDriver:
    """Tests for initialize_browser_driver function."""

    @patch("agent_core_utils.services.ChromeDriverManager")
    @patch("agent_core_utils.services.webdriver.Chrome")
    def test_initialize_browser_driver_success(self, mock_chrome, mock_driver_manager):
        """Test successful browser driver initialization."""
        mock_manager = Mock()
        mock_manager.install.return_value = "/path/to/chromedriver"
        mock_driver_manager.return_value = mock_manager
        
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        result = initialize_browser_driver()
        
        assert result == mock_driver
        mock_chrome.assert_called_once()

    @patch("agent_core_utils.services.ChromeDriverManager")
    @patch("agent_core_utils.services.webdriver.Chrome")
    def test_initialize_browser_driver_fallback_to_dummy(self, mock_chrome, mock_driver_manager):
        """Test fallback to dummy driver when Chrome initialization fails."""
        mock_manager = Mock()
        mock_manager.install.return_value = "/path/to/chromedriver"
        mock_driver_manager.return_value = mock_manager
        
        # Make Chrome initialization fail
        mock_chrome.side_effect = Exception("Chrome failed")
        
        result = initialize_browser_driver()
        
        # Should return a dummy driver
        assert hasattr(result, "get")
        assert hasattr(result, "quit")
        assert hasattr(result, "save_screenshot")
        assert hasattr(result, "page_source")

    @patch("agent_core_utils.services.ChromeDriverManager")
    @patch("agent_core_utils.services.webdriver.Chrome")
    def test_initialize_browser_driver_chromedriver_download_fails(self, mock_chrome, mock_driver_manager):
        """Test fallback to system chromedriver when download fails."""
        # Make ChromeDriverManager fail
        mock_driver_manager.side_effect = Exception("Download failed")
        
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        result = initialize_browser_driver()
        
        assert result == mock_driver
        # Should still create Chrome driver with fallback path
        mock_chrome.assert_called_once()


class TestGetRedisClient:
    """Tests for get_redis_client function."""

    def test_get_redis_client_default_config(self, monkeypatch):
        """Test Redis client initialization with default configuration."""
        # Clear environment variables to test defaults
        monkeypatch.delenv("REDIS_HOST", raising=False)
        monkeypatch.delenv("REDIS_PORT", raising=False)
        monkeypatch.delenv("REDIS_DB", raising=False)
        monkeypatch.delenv("REDIS_USERNAME", raising=False)
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)
        
        with patch("agent_core_utils.services.redis.Redis") as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            
            result = get_redis_client()
            
            assert result == mock_client
            mock_redis.assert_called_once_with(
                host="localhost",
                port=6379,
                db=0,
                username="default",
                password=None,
            )

    def test_get_redis_client_custom_config(self, monkeypatch):
        """Test Redis client initialization with custom configuration."""
        # The fixture already resets the client, no need to do it again
        
        monkeypatch.setenv("REDIS_HOST", "redis.example.com")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("REDIS_DB", "1")
        monkeypatch.setenv("REDIS_USERNAME", "user")
        monkeypatch.setenv("REDIS_PASSWORD", "pass")
        
        with patch("agent_core_utils.services.redis.Redis") as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            
            result = get_redis_client()
            
            assert result == mock_client
            mock_redis.assert_called_once_with(
                host="redis.example.com",
                port=6380,
                db=1,
                username="user",
                password="pass",
            )

    def test_get_redis_client_singleton_behavior(self, monkeypatch):
        """Test that get_redis_client returns the same instance on multiple calls."""
        monkeypatch.delenv("REDIS_HOST", raising=False)
        
        with patch("agent_core_utils.services.redis.Redis") as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            
            # The fixture already resets the client, so it will be None initially
            
            result1 = get_redis_client()
            result2 = get_redis_client()
            
            assert result1 == result2
            # Should only create client once
            mock_redis.assert_called_once()


class TestGetRedisUrl:
    """Tests for get_redis_url function."""

    def test_get_redis_url_from_env_variable(self, monkeypatch):
        """Test Redis URL generation from REDIS_URL environment variable."""
        monkeypatch.setenv("REDIS_URL", "redis://user:pass@redis.example.com:6379/0")
        
        result = get_redis_url()
        
        assert result == "redis://user:pass@redis.example.com:6379/0"

    def test_get_redis_url_from_components(self, monkeypatch):
        """Test Redis URL generation from component environment variables."""
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.setenv("REDIS_HOST", "redis.example.com")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("REDIS_DB", "1")
        monkeypatch.setenv("REDIS_USERNAME", "user")
        monkeypatch.setenv("REDIS_PASSWORD", "pass")
        
        result = get_redis_url()
        
        assert result == "redis://user:pass@redis.example.com:6380/1"

    def test_get_redis_url_minimal_config(self, monkeypatch):
        """Test Redis URL generation with minimal configuration."""
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.delenv("REDIS_PORT", raising=False)
        monkeypatch.delenv("REDIS_DB", raising=False)
        monkeypatch.delenv("REDIS_USERNAME", raising=False)
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)
        
        result = get_redis_url()
        
        assert result == "redis://localhost:6379/0"

    def test_get_redis_url_no_host(self, monkeypatch):
        """Test Redis URL generation when no host is configured."""
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.delenv("REDIS_HOST", raising=False)
        
        result = get_redis_url()
        
        assert result is None

    def test_get_redis_url_password_only(self, monkeypatch):
        """Test Redis URL generation with password but no username."""
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.delenv("REDIS_USERNAME", raising=False)
        monkeypatch.setenv("REDIS_PASSWORD", "secret")
        
        result = get_redis_url()
        
        assert result == "redis://:secret@localhost:6379/0"
