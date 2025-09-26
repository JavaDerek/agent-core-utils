"""Tests for CommunicationConfig class."""

import pytest
from pydantic import ValidationError

from agent_core_utils.config import CommunicationConfig


class TestCommunicationConfig:
    """Test CommunicationConfig class functionality."""

    def test_config_creation_with_defaults(self):
        """Test creating CommunicationConfig with default values."""
        config = CommunicationConfig()
        
        # Verify Redis connection defaults
        assert config.redis_host == "localhost"
        assert config.redis_port == 6379
        assert config.redis_password is None
        
        # Verify stream settings defaults
        assert config.stream_max_length == 10000
        assert config.read_block_timeout == 1000
        assert config.read_batch_size == 100
        
        # Verify retry settings defaults
        assert config.max_retries == 3
        assert config.retry_backoff_factor == 2.0
        assert config.max_retry_delay == 300
        
        # Verify task timeout defaults
        assert config.acknowledgment_timeout == 30
        assert config.task_timeout == 3600
        
        # Verify cleanup settings defaults
        assert config.cleanup_interval == 3600
        assert config.max_task_age == 86400

    def test_config_creation_with_custom_values(self):
        """Test creating CommunicationConfig with custom values."""
        config = CommunicationConfig(
            redis_host="redis.example.com",
            redis_port=6380,
            redis_password="secret123",
            stream_max_length=5000,
            read_block_timeout=2000,
            read_batch_size=50,
            max_retries=5,
            retry_backoff_factor=1.5,
            max_retry_delay=600,
            acknowledgment_timeout=60,
            task_timeout=7200,
            cleanup_interval=1800,
            max_task_age=43200
        )
        
        # Verify all custom values are set
        assert config.redis_host == "redis.example.com"
        assert config.redis_port == 6380
        assert config.redis_password == "secret123"
        assert config.stream_max_length == 5000
        assert config.read_block_timeout == 2000
        assert config.read_batch_size == 50
        assert config.max_retries == 5
        assert config.retry_backoff_factor == 1.5
        assert config.max_retry_delay == 600
        assert config.acknowledgment_timeout == 60
        assert config.task_timeout == 7200
        assert config.cleanup_interval == 1800
        assert config.max_task_age == 43200

    def test_redis_port_validation(self):
        """Test Redis port validation."""
        # Valid ports should work
        valid_ports = [1, 6379, 6380, 65535]
        for port in valid_ports:
            config = CommunicationConfig(redis_port=port)
            assert config.redis_port == port
        
        # Invalid ports should raise validation error
        invalid_ports = [0, -1, 65536, 100000]
        for port in invalid_ports:
            with pytest.raises(ValidationError):
                CommunicationConfig(redis_port=port)

    def test_stream_max_length_validation(self):
        """Test stream max length validation."""
        # Valid lengths
        valid_lengths = [1, 1000, 10000, 100000]
        for length in valid_lengths:
            config = CommunicationConfig(stream_max_length=length)
            assert config.stream_max_length == length
        
        # Invalid lengths
        invalid_lengths = [0, -1, -100]
        for length in invalid_lengths:
            with pytest.raises(ValidationError):
                CommunicationConfig(stream_max_length=length)

    def test_timeout_validation(self):
        """Test timeout field validation."""
        # Valid timeouts
        valid_timeouts = [1, 30, 3600, 86400]
        for timeout in valid_timeouts:
            config = CommunicationConfig(
                read_block_timeout=timeout,
                acknowledgment_timeout=timeout,
                task_timeout=timeout,
                cleanup_interval=timeout,
                max_task_age=timeout
            )
            assert config.read_block_timeout == timeout
            assert config.acknowledgment_timeout == timeout
            assert config.task_timeout == timeout
            assert config.cleanup_interval == timeout
            assert config.max_task_age == timeout
        
        # Invalid timeouts (negative values)
        invalid_timeouts = [-1, -100]
        for timeout in invalid_timeouts:
            with pytest.raises(ValidationError):
                CommunicationConfig(read_block_timeout=timeout)
            
            with pytest.raises(ValidationError):
                CommunicationConfig(acknowledgment_timeout=timeout)
            
            with pytest.raises(ValidationError):
                CommunicationConfig(task_timeout=timeout)

    def test_retry_settings_validation(self):
        """Test retry settings validation."""
        # Valid retry settings
        config = CommunicationConfig(
            max_retries=10,
            retry_backoff_factor=3.0,
            max_retry_delay=1200
        )
        assert config.max_retries == 10
        assert config.retry_backoff_factor == 3.0
        assert config.max_retry_delay == 1200
        
        # Invalid max_retries
        with pytest.raises(ValidationError):
            CommunicationConfig(max_retries=-1)
        
        with pytest.raises(ValidationError):
            CommunicationConfig(max_retries=0)
        
        # Invalid retry_backoff_factor
        with pytest.raises(ValidationError):
            CommunicationConfig(retry_backoff_factor=0.0)
        
        with pytest.raises(ValidationError):
            CommunicationConfig(retry_backoff_factor=-1.0)
        
        # Invalid max_retry_delay
        with pytest.raises(ValidationError):
            CommunicationConfig(max_retry_delay=0)
        
        with pytest.raises(ValidationError):
            CommunicationConfig(max_retry_delay=-1)

    def test_read_batch_size_validation(self):
        """Test read batch size validation."""
        # Valid batch sizes
        valid_sizes = [1, 10, 100, 1000]
        for size in valid_sizes:
            config = CommunicationConfig(read_batch_size=size)
            assert config.read_batch_size == size
        
        # Invalid batch sizes
        invalid_sizes = [0, -1, -100]
        for size in invalid_sizes:
            with pytest.raises(ValidationError):
                CommunicationConfig(read_batch_size=size)

    def test_redis_host_validation(self):
        """Test Redis host validation."""
        # Valid hostnames/IPs
        valid_hosts = [
            "localhost",
            "redis.example.com",
            "127.0.0.1",
            "192.168.1.100",
            "redis-cluster-01.internal",
            "my-redis-server"
        ]
        
        for host in valid_hosts:
            config = CommunicationConfig(redis_host=host)
            assert config.redis_host == host
        
        # Empty host should fail
        with pytest.raises(ValidationError):
            CommunicationConfig(redis_host="")

    def test_redis_password_optional(self):
        """Test that Redis password is optional."""
        # None should be allowed
        config = CommunicationConfig(redis_password=None)
        assert config.redis_password is None
        
        # String should be allowed
        config = CommunicationConfig(redis_password="my_password")
        assert config.redis_password == "my_password"
        
        # Empty string should be allowed (some Redis configs use empty passwords)
        config = CommunicationConfig(redis_password="")
        assert config.redis_password == ""

    def test_config_serialization(self):
        """Test configuration serialization to/from dict."""
        original_config = CommunicationConfig(
            redis_host="test.redis.com",
            redis_port=6380,
            redis_password="test_password",
            max_retries=5
        )
        
        # Serialize to dict
        config_dict = original_config.dict()
        assert isinstance(config_dict, dict)
        assert config_dict["redis_host"] == "test.redis.com"
        assert config_dict["redis_port"] == 6380
        assert config_dict["redis_password"] == "test_password"
        assert config_dict["max_retries"] == 5
        
        # Deserialize from dict
        restored_config = CommunicationConfig(**config_dict)
        assert restored_config.redis_host == original_config.redis_host
        assert restored_config.redis_port == original_config.redis_port
        assert restored_config.redis_password == original_config.redis_password
        assert restored_config.max_retries == original_config.max_retries

    def test_config_json_serialization(self):
        """Test configuration JSON serialization."""
        config = CommunicationConfig(
            redis_host="json.test.com",
            stream_max_length=5000,
            retry_backoff_factor=2.5
        )
        
        # Serialize to JSON
        config_json = config.json()
        assert isinstance(config_json, str)
        assert "json.test.com" in config_json
        assert "5000" in config_json
        assert "2.5" in config_json
        
        # Deserialize from JSON
        restored_config = CommunicationConfig.parse_raw(config_json)
        assert restored_config.redis_host == config.redis_host
        assert restored_config.stream_max_length == config.stream_max_length
        assert restored_config.retry_backoff_factor == config.retry_backoff_factor

    def test_config_environment_integration(self):
        """Test configuration integration with environment variables."""
        import os
        from unittest.mock import patch
        
        # Mock environment variables
        env_vars = {
            'REDIS_HOST': 'env.redis.com',
            'REDIS_PORT': '6381',
            'REDIS_PASSWORD': 'env_password',
            'STREAM_MAX_LENGTH': '20000',
            'MAX_RETRIES': '7'
        }
        
        with patch.dict(os.environ, env_vars):
            # This would require the actual config class to support environment variables
            # For now, we'll test manual creation with env values
            config = CommunicationConfig(
                redis_host=os.getenv('REDIS_HOST', 'localhost'),
                redis_port=int(os.getenv('REDIS_PORT', '6379')),
                redis_password=os.getenv('REDIS_PASSWORD'),
                stream_max_length=int(os.getenv('STREAM_MAX_LENGTH', '10000')),
                max_retries=int(os.getenv('MAX_RETRIES', '3'))
            )
            
            assert config.redis_host == 'env.redis.com'
            assert config.redis_port == 6381
            assert config.redis_password == 'env_password'
            assert config.stream_max_length == 20000
            assert config.max_retries == 7

    def test_config_validation_edge_cases(self):
        """Test configuration validation edge cases."""
        # Very large but valid values
        config = CommunicationConfig(
            stream_max_length=1000000,
            read_block_timeout=86400000,  # 24 hours in ms
            task_timeout=604800,  # 1 week in seconds
            max_retry_delay=3600,  # 1 hour
            retry_backoff_factor=10.0
        )
        
        assert config.stream_max_length == 1000000
        assert config.read_block_timeout == 86400000
        assert config.task_timeout == 604800
        assert config.max_retry_delay == 3600
        assert config.retry_backoff_factor == 10.0

    def test_config_realistic_production_values(self):
        """Test configuration with realistic production values."""
        production_config = CommunicationConfig(
            redis_host="redis-cluster.production.com",
            redis_port=6379,
            redis_password="super_secure_password_123",
            stream_max_length=50000,  # Larger for production
            read_block_timeout=5000,  # 5 second timeout
            read_batch_size=200,  # Larger batches
            max_retries=5,  # More retries for production
            retry_backoff_factor=2.0,
            max_retry_delay=900,  # 15 minutes max delay
            acknowledgment_timeout=60,  # 1 minute for ack
            task_timeout=7200,  # 2 hours for task completion
            cleanup_interval=1800,  # Clean up every 30 minutes
            max_task_age=172800  # Keep tasks for 2 days
        )
        
        # Verify all production values
        assert production_config.redis_host == "redis-cluster.production.com"
        assert production_config.stream_max_length == 50000
        assert production_config.read_block_timeout == 5000
        assert production_config.read_batch_size == 200
        assert production_config.max_retries == 5
        assert production_config.max_retry_delay == 900
        assert production_config.acknowledgment_timeout == 60
        assert production_config.task_timeout == 7200
        assert production_config.cleanup_interval == 1800
        assert production_config.max_task_age == 172800

    def test_config_development_values(self):
        """Test configuration with development-friendly values."""
        dev_config = CommunicationConfig(
            redis_host="localhost",
            redis_port=6379,
            redis_password=None,  # No password for dev
            stream_max_length=1000,  # Smaller for dev
            read_block_timeout=1000,  # 1 second timeout
            read_batch_size=10,  # Smaller batches for debugging
            max_retries=2,  # Fewer retries for faster feedback
            retry_backoff_factor=1.5,
            max_retry_delay=30,  # 30 seconds max for dev
            acknowledgment_timeout=10,  # Quick ack for dev
            task_timeout=300,  # 5 minutes for dev tasks
            cleanup_interval=300,  # Clean up every 5 minutes
            max_task_age=3600  # Keep tasks for 1 hour only
        )
        
        # Verify development values
        assert dev_config.redis_host == "localhost"
        assert dev_config.redis_password is None
        assert dev_config.stream_max_length == 1000
        assert dev_config.read_batch_size == 10
        assert dev_config.max_retries == 2
        assert dev_config.max_retry_delay == 30
        assert dev_config.acknowledgment_timeout == 10
        assert dev_config.task_timeout == 300

    def test_config_copy_and_update(self):
        """Test configuration copying and updating."""
        base_config = CommunicationConfig(
            redis_host="base.redis.com",
            max_retries=3
        )
        
        # Test creating updated config
        updated_config = CommunicationConfig(
            **{**base_config.dict(), "redis_host": "updated.redis.com", "max_retries": 5}
        )
        
        # Verify base config unchanged
        assert base_config.redis_host == "base.redis.com"
        assert base_config.max_retries == 3
        
        # Verify updated config has changes
        assert updated_config.redis_host == "updated.redis.com"
        assert updated_config.max_retries == 5
        
        # Verify other values copied
        assert updated_config.redis_port == base_config.redis_port
        assert updated_config.stream_max_length == base_config.stream_max_length

    def test_config_field_types(self):
        """Test that config fields have correct types."""
        config = CommunicationConfig()
        
        # String fields
        assert isinstance(config.redis_host, str)
        assert isinstance(config.redis_password, (str, type(None)))
        
        # Integer fields
        assert isinstance(config.redis_port, int)
        assert isinstance(config.stream_max_length, int)
        assert isinstance(config.read_block_timeout, int)
        assert isinstance(config.read_batch_size, int)
        assert isinstance(config.max_retries, int)
        assert isinstance(config.max_retry_delay, int)
        assert isinstance(config.acknowledgment_timeout, int)
        assert isinstance(config.task_timeout, int)
        assert isinstance(config.cleanup_interval, int)
        assert isinstance(config.max_task_age, int)
        
        # Float fields
        assert isinstance(config.retry_backoff_factor, float)