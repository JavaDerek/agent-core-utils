"""Tests for RedisStreamManager class."""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from agent_core_utils.redis_streams import RedisStreamManager


class TestRedisStreamManager:
    """Test RedisStreamManager class functionality."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        mock_redis = AsyncMock()
        return mock_redis

    @pytest.fixture
    def stream_manager(self, mock_redis_client):
        """Create a RedisStreamManager instance with mock Redis client."""
        return RedisStreamManager(mock_redis_client)

    @pytest.fixture
    def sample_message_data(self):
        """Create sample message data for testing."""
        return {
            "task_id": "test_task_1",
            "thread_id": "thread_123",
            "description": "Test task description",
            "priority": 8,
            "assigned_to": "bear",
            "created_at": datetime.now().isoformat()
        }

    def test_stream_manager_initialization(self, mock_redis_client):
        """Test RedisStreamManager initialization."""
        manager = RedisStreamManager(mock_redis_client)
        
        assert manager.redis == mock_redis_client

    async def test_send_message_basic(self, stream_manager, mock_redis_client, sample_message_data):
        """Test basic message sending to Redis stream."""
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        message_id = await stream_manager.send_message("bear:commands", sample_message_data)
        
        # Verify message ID is returned as string
        assert message_id == "1234567890-0"
        
        # Verify Redis xadd was called correctly
        mock_redis_client.xadd.assert_called_once()
        call_args = mock_redis_client.xadd.call_args
        
        # Check stream name
        assert call_args[0][0] == "bear:commands"
        
        # Check message data was serialized
        sent_data = call_args[0][1]
        assert sent_data["task_id"] == "test_task_1"
        assert sent_data["description"] == "Test task description"

    async def test_send_message_with_max_length(self, stream_manager, mock_redis_client, sample_message_data):
        """Test sending message with stream length limit."""
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        await stream_manager.send_message("test:stream", sample_message_data, max_length=5000)
        
        # Verify maxlen parameter was passed
        call_args = mock_redis_client.xadd.call_args
        call_kwargs = call_args[1] if len(call_args) > 1 else {}
        
        # Should include maxlen in call
        assert "maxlen" in call_kwargs or "maxlen" in str(call_args)

    async def test_send_message_complex_data_serialization(self, stream_manager, mock_redis_client):
        """Test sending message with complex nested data."""
        complex_data = {
            "task_id": "complex_task",
            "metadata": {
                "nested_object": {"key": "value"},
                "list_data": [1, 2, 3],
                "datetime_field": datetime.now().isoformat()
            },
            "tags": ["urgent", "festival", "booking"],
            "constraints": {
                "budget": 10000.50,
                "deadline": (datetime.now() + timedelta(days=7)).isoformat()
            }
        }
        
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        await stream_manager.send_message("test:stream", complex_data)
        
        # Verify complex data was properly serialized
        call_args = mock_redis_client.xadd.call_args
        sent_data = call_args[0][1]
        
        # Check that nested objects were JSON serialized
        assert "metadata" in sent_data
        metadata = json.loads(sent_data["metadata"])
        assert metadata["nested_object"]["key"] == "value"
        assert metadata["list_data"] == [1, 2, 3]
        
        # Check that lists were JSON serialized
        tags = json.loads(sent_data["tags"])
        assert "urgent" in tags
        assert len(tags) == 3

    async def test_send_message_redis_error(self, stream_manager, mock_redis_client, sample_message_data):
        """Test error handling when Redis send fails."""
        mock_redis_client.xadd = AsyncMock(side_effect=Exception("Redis connection failed"))
        
        with pytest.raises(Exception) as exc_info:
            await stream_manager.send_message("test:stream", sample_message_data)
        
        assert "Redis connection failed" in str(exc_info.value)

    async def test_read_messages_basic(self, stream_manager, mock_redis_client):
        """Test basic message reading from Redis streams."""
        # Mock Redis xread response
        mock_response = [
            (
                b"bear:commands",
                [
                    (
                        b"1234567890-0",
                        {
                            b"task_id": b"task_1",
                            b"description": b"First task"
                        }
                    ),
                    (
                        b"1234567890-1",
                        {
                            b"task_id": b"task_2",
                            b"description": b"Second task"
                        }
                    )
                ]
            )
        ]
        
        mock_redis_client.xread = AsyncMock(return_value=mock_response)
        
        streams = {"bear:commands": "0"}
        messages = await stream_manager.read_messages(streams)
        
        # Verify messages are properly formatted
        assert "bear:commands" in messages
        stream_messages = messages["bear:commands"]
        assert len(stream_messages) == 2
        
        # Check first message
        msg_id, msg_data = stream_messages[0]
        assert msg_id == "1234567890-0"
        assert msg_data["task_id"] == "task_1"
        
        # Check second message
        msg_id, msg_data = stream_messages[1]
        assert msg_id == "1234567890-1"
        assert msg_data["task_id"] == "task_2"

    async def test_read_messages_multiple_streams(self, stream_manager, mock_redis_client):
        """Test reading from multiple streams simultaneously."""
        mock_response = [
            (
                b"bear:commands",
                [
                    (
                        b"1234567890-0",
                        {b"task_id": b"bear_task"}
                    )
                ]
            ),
            (
                b"bobo:commands",
                [
                    (
                        b"1234567891-0",
                        {b"task_id": b"bobo_task"}
                    )
                ]
            )
        ]
        
        mock_redis_client.xread = AsyncMock(return_value=mock_response)
        
        streams = {
            "bear:commands": "0",
            "bobo:commands": "0"
        }
        
        messages = await stream_manager.read_messages(streams)
        
        # Verify both streams returned data
        assert "bear:commands" in messages
        assert "bobo:commands" in messages
        
        bear_msg = messages["bear:commands"][0][1]
        bobo_msg = messages["bobo:commands"][0][1]
        
        assert bear_msg["task_id"] == "bear_task"
        assert bobo_msg["task_id"] == "bobo_task"

    async def test_read_messages_with_blocking(self, stream_manager, mock_redis_client):
        """Test reading messages with blocking behavior."""
        mock_redis_client.xread = AsyncMock(return_value=[])
        
        streams = {"test:stream": "$"}
        
        await stream_manager.read_messages(streams, block=5000, count=50)
        
        # Verify blocking parameters were passed
        call_args = mock_redis_client.xread.call_args
        call_kwargs = call_args[1]
        
        assert call_kwargs.get("block") == 5000
        assert call_kwargs.get("count") == 50

    async def test_read_messages_empty_response(self, stream_manager, mock_redis_client):
        """Test reading when no messages are available."""
        mock_redis_client.xread = AsyncMock(return_value=[])
        
        streams = {"test:stream": "0"}
        messages = await stream_manager.read_messages(streams)
        
        assert messages == {}

    async def test_read_messages_with_last_ids(self, stream_manager, mock_redis_client):
        """Test reading messages with tracked last IDs."""
        mock_redis_client.xread = AsyncMock(return_value=[])
        
        streams = {"stream1": "1234567890-0", "stream2": "$"}
        last_ids = {"stream1": "1234567890-0", "stream2": "1234567891-0"}
        
        await stream_manager.read_messages(streams, last_ids=last_ids)
        
        # Verify Redis was called with correct stream positions
        call_args = mock_redis_client.xread.call_args
        streams_param = call_args[1]["streams"]
        
        # Should use provided last_ids or stream defaults
        assert "stream1" in streams_param
        assert "stream2" in streams_param

    async def test_create_consumer_group(self, stream_manager, mock_redis_client):
        """Test creating a consumer group."""
        mock_redis_client.xgroup_create = AsyncMock(return_value=True)
        
        await stream_manager.create_consumer_group("test:stream", "test_group", "0")
        
        # Verify Redis xgroup_create was called
        mock_redis_client.xgroup_create.assert_called_once_with(
            "test:stream", "test_group", "0", mkstream=True
        )

    async def test_create_consumer_group_already_exists(self, stream_manager, mock_redis_client):
        """Test creating consumer group when it already exists."""
        # Mock Redis to raise BUSYGROUP error
        mock_redis_client.xgroup_create = AsyncMock(
            side_effect=Exception("BUSYGROUP Consumer Group name already exists")
        )
        
        # Should handle the error gracefully
        await stream_manager.create_consumer_group("test:stream", "existing_group")
        
        # Should not raise exception for existing group
        mock_redis_client.xgroup_create.assert_called_once()

    async def test_read_consumer_group(self, stream_manager, mock_redis_client):
        """Test reading messages using consumer group."""
        # Mock Redis xreadgroup response
        mock_response = [
            (
                b"test:stream",
                [
                    (
                        b"1234567890-0",
                        {
                            b"task_id": b"group_task_1",
                            b"data": b"test_data"
                        }
                    )
                ]
            )
        ]
        
        mock_redis_client.xreadgroup = AsyncMock(return_value=mock_response)
        
        messages = await stream_manager.read_consumer_group(
            "test:stream", "test_group", "consumer1", count=10
        )
        
        # Verify messages are returned
        assert "test:stream" in messages
        msg_id, msg_data = messages["test:stream"][0]
        assert msg_id == "1234567890-0"
        assert msg_data["task_id"] == "group_task_1"
        
        # Verify Redis was called correctly
        mock_redis_client.xreadgroup.assert_called_once()
        call_args = mock_redis_client.xreadgroup.call_args
        assert call_args[0][0] == "test_group"  # Group name
        assert call_args[0][1] == "consumer1"   # Consumer name

    async def test_ack_message(self, stream_manager, mock_redis_client):
        """Test acknowledging a message."""
        mock_redis_client.xack = AsyncMock(return_value=1)
        
        await stream_manager.ack_message("test:stream", "test_group", "1234567890-0")
        
        # Verify Redis xack was called
        mock_redis_client.xack.assert_called_once_with(
            "test:stream", "test_group", "1234567890-0"
        )

    async def test_get_stream_info(self, stream_manager, mock_redis_client):
        """Test getting stream information."""
        mock_info = {
            b"length": 100,
            b"last_generated_id": b"1234567890-5",
            b"first_entry": [b"1234567800-0", [b"field", b"value"]],
            b"last_entry": [b"1234567890-5", [b"field", b"value"]]
        }
        
        mock_redis_client.xinfo_stream = AsyncMock(return_value=mock_info)
        
        info = await stream_manager.get_stream_info("test:stream")
        
        # Verify info is properly formatted
        assert info["length"] == 100
        assert info["last_generated_id"] == "1234567890-5"
        assert "first_entry" in info
        assert "last_entry" in info
        
        mock_redis_client.xinfo_stream.assert_called_once_with("test:stream")

    async def test_trim_stream(self, stream_manager, mock_redis_client):
        """Test trimming stream to max length."""
        mock_redis_client.xtrim = AsyncMock(return_value=50)  # Number of messages removed
        
        removed_count = await stream_manager.trim_stream("test:stream", 1000)
        
        assert removed_count == 50
        
        # Verify Redis xtrim was called
        mock_redis_client.xtrim.assert_called_once_with(
            "test:stream", maxlen=1000, approximate=True
        )

    async def test_data_type_handling(self, stream_manager, mock_redis_client):
        """Test proper handling of different data types in messages."""
        # Test data with various types
        test_data = {
            "string_field": "test_string",
            "int_field": 42,
            "float_field": 3.14,
            "bool_field": True,
            "null_field": None,
            "datetime_field": datetime.now().isoformat(),
            "list_field": ["a", "b", "c"],
            "dict_field": {"nested": "value"}
        }
        
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        await stream_manager.send_message("test:stream", test_data)
        
        # Verify all data types were properly serialized
        call_args = mock_redis_client.xadd.call_args
        sent_data = call_args[0][1]
        
        # String should be passed as-is
        assert sent_data["string_field"] == "test_string"
        
        # Numbers should be converted to strings
        assert sent_data["int_field"] == "42"
        assert sent_data["float_field"] == "3.14"
        
        # Complex types should be JSON serialized
        list_data = json.loads(sent_data["list_field"])
        assert list_data == ["a", "b", "c"]
        
        dict_data = json.loads(sent_data["dict_field"])
        assert dict_data["nested"] == "value"

    async def test_redis_connection_error_handling(self, stream_manager, mock_redis_client):
        """Test handling of Redis connection errors."""
        # Mock Redis to simulate connection errors
        mock_redis_client.xread = AsyncMock(side_effect=ConnectionError("Redis server unavailable"))
        
        with pytest.raises(ConnectionError):
            await stream_manager.read_messages({"test:stream": "0"})

    async def test_stream_does_not_exist_handling(self, stream_manager, mock_redis_client):
        """Test handling when stream doesn't exist."""
        # Mock Redis to return empty response for non-existent stream
        mock_redis_client.xread = AsyncMock(return_value=[])
        
        messages = await stream_manager.read_messages({"nonexistent:stream": "0"})
        
        # Should return empty dict without error
        assert messages == {}

    async def test_message_deserialization_from_redis(self, stream_manager, mock_redis_client):
        """Test proper deserialization of messages from Redis."""
        # Mock Redis response with byte strings (as Redis returns)
        mock_response = [
            (
                b"test:stream",
                [
                    (
                        b"1234567890-0",
                        {
                            b"simple_field": b"simple_value",
                            b"json_field": b'{"nested": "data", "number": 42}',
                            b"list_field": b'["item1", "item2", "item3"]',
                            b"datetime_field": b"2025-09-24T10:00:00"
                        }
                    )
                ]
            )
        ]
        
        mock_redis_client.xread = AsyncMock(return_value=mock_response)
        
        messages = await stream_manager.read_messages({"test:stream": "0"})
        
        # Verify deserialization
        msg_id, msg_data = messages["test:stream"][0]
        
        # Simple fields should be decoded from bytes
        assert msg_data["simple_field"] == "simple_value"
        
        # JSON fields should be parsed if they look like JSON
        if isinstance(msg_data.get("json_field"), str) and msg_data["json_field"].startswith("{"):
            json_data = json.loads(msg_data["json_field"])
            assert json_data["nested"] == "data"
            assert json_data["number"] == 42

    async def test_concurrent_stream_operations(self, stream_manager, mock_redis_client):
        """Test concurrent stream operations."""
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        # Create multiple concurrent send operations
        send_tasks = [
            stream_manager.send_message(f"stream_{i}", {"task_id": f"task_{i}"})
            for i in range(5)
        ]
        
        # Execute concurrently
        message_ids = await asyncio.gather(*send_tasks)
        
        # Verify all succeeded
        assert len(message_ids) == 5
        assert all(msg_id == "1234567890-0" for msg_id in message_ids)
        assert mock_redis_client.xadd.call_count == 5


class TestRedisStreamManagerIntegration:
    """Integration tests for RedisStreamManager with complex scenarios."""

    @pytest.fixture
    def stream_manager(self):
        """Create stream manager with realistic setup."""
        mock_redis = AsyncMock()
        return RedisStreamManager(mock_redis)

    async def test_agent_communication_simulation(self, stream_manager):
        """Test simulated agent-to-agent communication via streams."""
        # Mock Redis for full communication flow
        stream_manager.redis.xadd = AsyncMock(return_value=b"msg_id")
        
        # Mock responses for different phases
        command_response = [
            (
                b"bear:commands",
                [
                    (
                        b"1234567890-0",
                        {
                            b"task_id": b"festival_task",
                            b"description": b"Research festivals",
                            b"priority": b"8"
                        }
                    )
                ]
            )
        ]
        
        response_response = [
            (
                b"responses:colonel",
                [
                    (
                        b"1234567891-0",
                        {
                            b"task_id": b"festival_task",
                            b"status": b"completed",
                            b"results": b'{"festivals_found": 5}'
                        }
                    )
                ]
            )
        ]
        
        stream_manager.redis.xread = AsyncMock(side_effect=[command_response, response_response])
        
        # 1. Colonel sends task to Bear
        task_data = {
            "task_id": "festival_task",
            "description": "Research European progressive rock festivals",
            "priority": 8,
            "assigned_to": "bear"
        }
        
        task_msg_id = await stream_manager.send_message("bear:commands", task_data)
        assert task_msg_id == "msg_id"
        
        # 2. Bear reads the task
        commands = await stream_manager.read_messages({"bear:commands": "0"})
        assert "bear:commands" in commands
        
        received_task = commands["bear:commands"][0][1]
        assert received_task["task_id"] == "festival_task"
        
        # 3. Bear sends response back
        response_data = {
            "task_id": "festival_task",
            "status": "completed",
            "results": {"festivals_found": 5, "bookings_secured": 2}
        }
        
        response_msg_id = await stream_manager.send_message("responses:colonel", response_data)
        assert response_msg_id == "msg_id"
        
        # 4. Colonel reads the response
        responses = await stream_manager.read_messages({"responses:colonel": "0"})
        assert "responses:colonel" in responses
        
        received_response = responses["responses:colonel"][0][1]
        assert received_response["task_id"] == "festival_task"
        assert received_response["status"] == "completed"

    async def test_consumer_group_workflow(self, stream_manager):
        """Test full consumer group workflow for reliable processing."""
        # Mock Redis operations
        stream_manager.redis.xgroup_create = AsyncMock(return_value=True)
        stream_manager.redis.xreadgroup = AsyncMock(return_value=[
            (
                b"work:queue",
                [
                    (
                        b"1234567890-0",
                        {
                            b"job_id": b"job_123",
                            b"work_type": b"festival_booking"
                        }
                    )
                ]
            )
        ])
        stream_manager.redis.xack = AsyncMock(return_value=1)
        
        # 1. Create consumer group
        await stream_manager.create_consumer_group("work:queue", "workers", "0")
        
        # 2. Read messages as consumer
        messages = await stream_manager.read_consumer_group(
            "work:queue", "workers", "worker-1", count=10
        )
        
        # 3. Process message and acknowledge
        assert "work:queue" in messages
        msg_id, msg_data = messages["work:queue"][0]
        
        # Simulate processing
        assert msg_data["job_id"] == "job_123"
        
        # 4. Acknowledge processing
        await stream_manager.ack_message("work:queue", "workers", msg_id)
        
        # Verify all operations were called
        stream_manager.redis.xgroup_create.assert_called_once()
        stream_manager.redis.xreadgroup.assert_called_once()
        stream_manager.redis.xack.assert_called_once()

    async def test_stream_maintenance_operations(self, stream_manager):
        """Test stream maintenance and monitoring operations."""
        # Mock stream info
        mock_info = {
            b"length": 1500,
            b"last_generated_id": b"1234567890-100",
            b"groups": 2
        }
        
        stream_manager.redis.xinfo_stream = AsyncMock(return_value=mock_info)
        stream_manager.redis.xtrim = AsyncMock(return_value=500)  # Messages removed
        
        # 1. Check stream info
        info = await stream_manager.get_stream_info("busy:stream")
        assert info["length"] == 1500
        
        # 2. Trim if too long
        if info["length"] > 1000:
            removed = await stream_manager.trim_stream("busy:stream", 1000)
            assert removed == 500
        
        # Verify operations
        stream_manager.redis.xinfo_stream.assert_called_once()
        stream_manager.redis.xtrim.assert_called_once()