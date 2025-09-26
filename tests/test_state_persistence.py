"""Tests for AgentStateManager class."""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta
import json

from agent_core_utils.state_persistence import AgentStateManager


class TestAgentStateManager:
    """Test AgentStateManager class functionality."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        mock_redis = AsyncMock()
        return mock_redis

    @pytest.fixture
    def state_manager(self, mock_redis_client):
        """Create an AgentStateManager instance with mock Redis client."""
        return AgentStateManager(mock_redis_client, "bear")

    @pytest.fixture
    def sample_stream_ids(self):
        """Create sample stream ID data for testing."""
        return {
            "bear:commands": "1234567890-0",
            "responses:colonel": "1234567891-5",
            "responses:sergeant": "1234567892-2"
        }

    @pytest.fixture
    def sample_active_tasks(self):
        """Create sample active tasks data for testing."""
        return [
            {
                "task_id": "task_1",
                "thread_id": "thread_1",
                "target_agent": "bear",
                "status": "acknowledged",
                "created_at": datetime.now().isoformat(),
                "last_response": {
                    "status": "acknowledged",
                    "timestamp": datetime.now().isoformat()
                }
            },
            {
                "task_id": "task_2",
                "thread_id": "thread_2",
                "target_agent": "bobo",
                "status": "in_progress",
                "created_at": (datetime.now() - timedelta(minutes=30)).isoformat(),
                "last_response": {
                    "status": "in_progress",
                    "timestamp": (datetime.now() - timedelta(minutes=15)).isoformat()
                }
            }
        ]

    @pytest.fixture
    def sample_agent_metadata(self):
        """Create sample agent metadata for testing."""
        return {
            "agent_name": "bear",
            "agent_type": "worker",
            "capabilities": ["festival_research", "booking_management"],
            "configuration": {
                "max_concurrent_tasks": 5,
                "timeout_seconds": 3600,
                "retry_attempts": 3
            },
            "last_startup": datetime.now().isoformat(),
            "version": "1.2.0",
            "status": "active"
        }

    def test_state_manager_initialization(self, mock_redis_client):
        """Test AgentStateManager initialization."""
        manager = AgentStateManager(mock_redis_client, "bear")
        
        assert manager.redis == mock_redis_client
        assert manager.agent_name == "bear"
        assert manager.state_key == "agent_state:bear"

    async def test_save_last_read_ids(self, state_manager, mock_redis_client, sample_stream_ids):
        """Test saving last read IDs for streams."""
        mock_redis_client.hset = AsyncMock(return_value=3)  # Number of fields set
        
        await state_manager.save_last_read_ids(sample_stream_ids)
        
        # Verify Redis hset was called correctly
        mock_redis_client.hset.assert_called_once()
        call_args = mock_redis_client.hset.call_args
        
        # Check the state key
        assert call_args[0][0] == "agent_state:bear"
        
        # Check that stream IDs were serialized
        mapping = call_args[1]["mapping"]
        assert "last_read_ids" in mapping
        
        # Verify data was JSON serialized
        saved_ids = json.loads(mapping["last_read_ids"])
        assert saved_ids["bear:commands"] == "1234567890-0"
        assert saved_ids["responses:colonel"] == "1234567891-5"

    async def test_load_last_read_ids(self, state_manager, mock_redis_client, sample_stream_ids):
        """Test loading last read IDs for streams."""
        # Mock Redis to return serialized stream IDs
        mock_redis_client.hget = AsyncMock(return_value=json.dumps(sample_stream_ids).encode())
        
        loaded_ids = await state_manager.load_last_read_ids()
        
        # Verify data was properly deserialized
        assert loaded_ids == sample_stream_ids
        assert loaded_ids["bear:commands"] == "1234567890-0"
        assert loaded_ids["responses:colonel"] == "1234567891-5"
        
        # Verify Redis was called correctly
        mock_redis_client.hget.assert_called_once_with("agent_state:bear", "last_read_ids")

    async def test_load_last_read_ids_not_found(self, state_manager, mock_redis_client):
        """Test loading last read IDs when none exist."""
        mock_redis_client.hget = AsyncMock(return_value=None)
        
        loaded_ids = await state_manager.load_last_read_ids()
        
        # Should return empty dict when no data exists
        assert loaded_ids == {}

    async def test_load_last_read_ids_corrupted_data(self, state_manager, mock_redis_client):
        """Test loading last read IDs with corrupted JSON data."""
        # Mock Redis to return invalid JSON
        mock_redis_client.hget = AsyncMock(return_value=b"invalid json data")
        
        loaded_ids = await state_manager.load_last_read_ids()
        
        # Should return empty dict when JSON is corrupted
        assert loaded_ids == {}

    async def test_save_active_tasks(self, state_manager, mock_redis_client, sample_active_tasks):
        """Test saving currently active tasks."""
        mock_redis_client.hset = AsyncMock(return_value=1)
        
        await state_manager.save_active_tasks(sample_active_tasks)
        
        # Verify Redis hset was called
        mock_redis_client.hset.assert_called_once()
        call_args = mock_redis_client.hset.call_args
        
        # Check state key and field
        assert call_args[0][0] == "agent_state:bear"
        mapping = call_args[1]["mapping"]
        assert "active_tasks" in mapping
        
        # Verify tasks were serialized
        saved_tasks = json.loads(mapping["active_tasks"])
        assert len(saved_tasks) == 2
        assert saved_tasks[0]["task_id"] == "task_1"
        assert saved_tasks[1]["status"] == "in_progress"

    async def test_load_active_tasks(self, state_manager, mock_redis_client, sample_active_tasks):
        """Test loading active tasks from previous session."""
        # Mock Redis to return serialized tasks
        mock_redis_client.hget = AsyncMock(return_value=json.dumps(sample_active_tasks).encode())
        
        loaded_tasks = await state_manager.load_active_tasks()
        
        # Verify data was properly deserialized
        assert len(loaded_tasks) == 2
        assert loaded_tasks[0]["task_id"] == "task_1"
        assert loaded_tasks[1]["status"] == "in_progress"
        assert loaded_tasks[0]["target_agent"] == "bear"
        
        # Verify Redis was called correctly
        mock_redis_client.hget.assert_called_once_with("agent_state:bear", "active_tasks")

    async def test_load_active_tasks_empty(self, state_manager, mock_redis_client):
        """Test loading active tasks when none exist."""
        mock_redis_client.hget = AsyncMock(return_value=None)
        
        loaded_tasks = await state_manager.load_active_tasks()
        
        # Should return empty list when no data exists
        assert loaded_tasks == []

    async def test_save_agent_metadata(self, state_manager, mock_redis_client, sample_agent_metadata):
        """Test saving agent configuration and status."""
        mock_redis_client.hset = AsyncMock(return_value=1)
        
        await state_manager.save_agent_metadata(sample_agent_metadata)
        
        # Verify Redis hset was called
        call_args = mock_redis_client.hset.call_args
        mapping = call_args[1]["mapping"]
        
        assert "agent_metadata" in mapping
        
        # Verify metadata was serialized
        saved_metadata = json.loads(mapping["agent_metadata"])
        assert saved_metadata["agent_name"] == "bear"
        assert saved_metadata["agent_type"] == "worker" 
        assert "festival_research" in saved_metadata["capabilities"]
        assert saved_metadata["configuration"]["max_concurrent_tasks"] == 5

    async def test_load_agent_metadata(self, state_manager, mock_redis_client, sample_agent_metadata):
        """Test loading agent configuration and status."""
        # Mock Redis to return serialized metadata
        mock_redis_client.hget = AsyncMock(return_value=json.dumps(sample_agent_metadata).encode())
        
        loaded_metadata = await state_manager.load_agent_metadata()
        
        # Verify data was properly deserialized
        assert loaded_metadata["agent_name"] == "bear"
        assert loaded_metadata["version"] == "1.2.0"
        assert loaded_metadata["configuration"]["timeout_seconds"] == 3600
        
        # Verify Redis was called correctly
        mock_redis_client.hget.assert_called_once_with("agent_state:bear", "agent_metadata")

    async def test_load_agent_metadata_not_found(self, state_manager, mock_redis_client):
        """Test loading agent metadata when none exists."""
        mock_redis_client.hget = AsyncMock(return_value=None)
        
        loaded_metadata = await state_manager.load_agent_metadata()
        
        # Should return empty dict when no data exists
        assert loaded_metadata == {}

    async def test_multiple_field_operations(self, state_manager, mock_redis_client):
        """Test operations that affect multiple state fields."""
        # Mock Redis operations
        mock_redis_client.hset = AsyncMock(return_value=2)
        mock_redis_client.hget = AsyncMock(side_effect=[
            json.dumps({"stream1": "id1"}).encode(),  # last_read_ids
            json.dumps([{"task_id": "task1"}]).encode()  # active_tasks
        ])
        
        # Save multiple types of data
        await state_manager.save_last_read_ids({"stream1": "id1"})
        await state_manager.save_active_tasks([{"task_id": "task1"}])
        
        # Load multiple types of data
        stream_ids = await state_manager.load_last_read_ids()
        tasks = await state_manager.load_active_tasks()
        
        # Verify both operations worked
        assert stream_ids["stream1"] == "id1"
        assert len(tasks) == 1
        assert tasks[0]["task_id"] == "task1"
        
        # Verify Redis was called correctly
        assert mock_redis_client.hset.call_count == 2
        assert mock_redis_client.hget.call_count == 2

    async def test_state_key_uniqueness(self, mock_redis_client):
        """Test that different agents have unique state keys."""
        bear_manager = AgentStateManager(mock_redis_client, "bear")
        bobo_manager = AgentStateManager(mock_redis_client, "bobo")
        colonel_manager = AgentStateManager(mock_redis_client, "colonel")
        
        # Verify unique state keys
        assert bear_manager.state_key == "agent_state:bear"
        assert bobo_manager.state_key == "agent_state:bobo"
        assert colonel_manager.state_key == "agent_state:colonel"
        
        # Verify they're all different
        keys = {bear_manager.state_key, bobo_manager.state_key, colonel_manager.state_key}
        assert len(keys) == 3

    async def test_redis_error_handling_on_save(self, state_manager, mock_redis_client):
        """Test error handling when Redis save operations fail."""
        mock_redis_client.hset = AsyncMock(side_effect=Exception("Redis connection lost"))
        
        with pytest.raises(Exception) as exc_info:
            await state_manager.save_last_read_ids({"stream": "id"})
        
        assert "Redis connection lost" in str(exc_info.value)

    async def test_redis_error_handling_on_load(self, state_manager, mock_redis_client):
        """Test error handling when Redis load operations fail."""
        mock_redis_client.hget = AsyncMock(side_effect=Exception("Redis read error"))
        
        # Should return default values instead of raising exceptions
        result = await state_manager.load_last_read_ids()
        assert result == {}
        
        result = await state_manager.load_active_tasks()
        assert result == []
        
        result = await state_manager.load_agent_metadata()
        assert result == {}

    async def test_large_data_serialization(self, state_manager, mock_redis_client):
        """Test serialization of large data structures."""
        # Create large active tasks list
        large_tasks = [
            {
                "task_id": f"task_{i}",
                "thread_id": f"thread_{i}",
                "description": f"Large task description {i} " * 100,  # Make it big
                "metadata": {
                    "large_list": list(range(100)),
                    "large_dict": {f"key_{j}": f"value_{j}" for j in range(50)}
                },
                "created_at": datetime.now().isoformat()
            }
            for i in range(20)
        ]
        
        mock_redis_client.hset = AsyncMock(return_value=1)
        
        # Should handle large data without issues
        await state_manager.save_active_tasks(large_tasks)
        
        # Verify it was saved
        mock_redis_client.hset.assert_called_once()
        call_args = mock_redis_client.hset.call_args
        mapping = call_args[1]["mapping"]
        
        # Verify the JSON is valid and large
        saved_json = mapping["active_tasks"]
        assert len(saved_json) > 10000  # Should be quite large
        
        # Should be parseable
        parsed_data = json.loads(saved_json)
        assert len(parsed_data) == 20

    async def test_datetime_serialization_handling(self, state_manager, mock_redis_client):
        """Test proper handling of datetime objects in state data."""
        now = datetime.now()
        
        # Data with datetime objects
        metadata_with_datetimes = {
            "last_startup": now,
            "last_task_completion": now - timedelta(hours=1),
            "next_scheduled_check": now + timedelta(minutes=30),
            "configuration": {
                "created_at": now - timedelta(days=7)
            }
        }
        
        mock_redis_client.hset = AsyncMock(return_value=1)
        
        # Should handle datetime serialization
        await state_manager.save_agent_metadata(metadata_with_datetimes)
        
        # Verify datetime objects were serialized
        call_args = mock_redis_client.hset.call_args
        mapping = call_args[1]["mapping"]
        saved_json = mapping["agent_metadata"]
        
        # Should be valid JSON (datetime objects converted to strings)
        parsed_data = json.loads(saved_json)
        
        # Datetime fields should be ISO format strings
        assert isinstance(parsed_data["last_startup"], str)
        assert "T" in parsed_data["last_startup"]  # ISO format indicator

    async def test_state_versioning_compatibility(self, state_manager, mock_redis_client):
        """Test compatibility with different state data versions."""
        # Simulate old version data (missing some fields)
        old_version_data = {
            "task_id": "old_task",
            "status": "in_progress"
            # Missing newer fields like 'thread_id', 'last_response', etc.
        }
        
        mock_redis_client.hget = AsyncMock(
            return_value=json.dumps([old_version_data]).encode()
        )
        
        # Should load old data without errors
        loaded_tasks = await state_manager.load_active_tasks()
        
        assert len(loaded_tasks) == 1
        assert loaded_tasks[0]["task_id"] == "old_task"
        assert loaded_tasks[0]["status"] == "in_progress"


class TestAgentStateManagerIntegration:
    """Integration tests for AgentStateManager with realistic scenarios."""

    @pytest.fixture
    def state_manager(self):
        """Create state manager with realistic setup."""
        mock_redis = AsyncMock()
        return AgentStateManager(mock_redis, "bear")

    async def test_agent_restart_recovery_simulation(self, state_manager):
        """Test complete agent restart and state recovery simulation."""
        # Simulate agent shutdown - save state
        pre_shutdown_stream_ids = {
            "bear:commands": "1234567890-15",
            "responses:colonel": "1234567891-8",
            "responses:sergeant": "1234567892-3"
        }
        
        pre_shutdown_tasks = [
            {
                "task_id": "urgent_task",
                "status": "in_progress",
                "created_at": datetime.now().isoformat(),
                "progress": {"current_step": "festival_research", "completion": 0.6}
            },
            {
                "task_id": "background_task",
                "status": "acknowledged",
                "created_at": (datetime.now() - timedelta(minutes=45)).isoformat()
            }
        ]
        
        pre_shutdown_metadata = {
            "last_shutdown": datetime.now().isoformat(),
            "active_connections": ["colonel", "sergeant"],
            "performance_stats": {"tasks_completed": 150, "avg_time": 120}
        }
        
        # Mock Redis save operations
        state_manager.redis.hset = AsyncMock(return_value=1)
        
        # Save all state before shutdown
        await state_manager.save_last_read_ids(pre_shutdown_stream_ids)
        await state_manager.save_active_tasks(pre_shutdown_tasks)
        await state_manager.save_agent_metadata(pre_shutdown_metadata)
        
        # Verify saves happened
        assert state_manager.redis.hset.call_count == 3
        
        # Simulate agent restart - load state
        state_manager.redis.hget = AsyncMock(side_effect=[
            json.dumps(pre_shutdown_stream_ids).encode(),
            json.dumps(pre_shutdown_tasks).encode(), 
            json.dumps(pre_shutdown_metadata).encode()
        ])
        
        # Load all state after restart
        recovered_stream_ids = await state_manager.load_last_read_ids()
        recovered_tasks = await state_manager.load_active_tasks()
        recovered_metadata = await state_manager.load_agent_metadata()
        
        # Verify complete state recovery
        assert recovered_stream_ids == pre_shutdown_stream_ids
        assert len(recovered_tasks) == 2
        assert recovered_tasks[0]["task_id"] == "urgent_task"
        assert recovered_tasks[0]["progress"]["completion"] == 0.6
        assert recovered_metadata["performance_stats"]["tasks_completed"] == 150

    async def test_incremental_state_updates(self, state_manager):
        """Test incremental state updates during agent operation."""
        # Mock Redis operations
        state_manager.redis.hset = AsyncMock(return_value=1)
        state_manager.redis.hget = AsyncMock()
        
        # Simulate agent operation with incremental updates
        initial_stream_ids = {"stream1": "100-0"}
        await state_manager.save_last_read_ids(initial_stream_ids)
        
        # Update stream positions as messages are processed  
        updated_stream_ids = {"stream1": "101-0", "stream2": "200-0"}
        await state_manager.save_last_read_ids(updated_stream_ids)
        
        # Add tasks as they come in
        initial_tasks = [{"task_id": "task1", "status": "acknowledged"}]
        await state_manager.save_active_tasks(initial_tasks)
        
        # Update tasks as they progress
        updated_tasks = [
            {"task_id": "task1", "status": "in_progress"},
            {"task_id": "task2", "status": "acknowledged"}
        ]
        await state_manager.save_active_tasks(updated_tasks)
        
        # Verify multiple saves happened
        assert state_manager.redis.hset.call_count == 4  # 2 stream updates + 2 task updates

    async def test_concurrent_state_operations(self, state_manager):
        """Test concurrent state save/load operations."""
        import asyncio
        
        state_manager.redis.hset = AsyncMock(return_value=1)
        state_manager.redis.hget = AsyncMock(return_value=json.dumps({}).encode())
        
        # Create concurrent save operations
        save_tasks = []
        for i in range(3):
            save_tasks.extend([
                state_manager.save_last_read_ids({f"stream_{i}": f"id_{i}"}),
                state_manager.save_active_tasks([{f"task_{i}": f"data_{i}"}]),
                state_manager.save_agent_metadata({f"meta_{i}": f"value_{i}"})
            ])
        
        # Execute all saves concurrently
        await asyncio.gather(*save_tasks)
        
        # Verify all operations completed
        assert state_manager.redis.hset.call_count == 9  # 3 operations × 3 iterations
        
        # Create concurrent load operations
        load_tasks = []
        for _ in range(3):
            load_tasks.extend([
                state_manager.load_last_read_ids(),
                state_manager.load_active_tasks(),
                state_manager.load_agent_metadata()
            ])
        
        # Execute all loads concurrently
        results = await asyncio.gather(*load_tasks)
        
        # Verify all operations completed
        assert len(results) == 9
        assert state_manager.redis.hget.call_count == 9

    async def test_state_cleanup_and_maintenance(self, state_manager):
        """Test state cleanup and maintenance operations."""
        # Mock Redis operations
        state_manager.redis.hget = AsyncMock(return_value=json.dumps([
            {
                "task_id": "old_completed_task",
                "status": "completed", 
                "completed_at": (datetime.now() - timedelta(days=2)).isoformat()
            },
            {
                "task_id": "recent_active_task",
                "status": "in_progress",
                "created_at": datetime.now().isoformat()
            },
            {
                "task_id": "stale_task",
                "status": "acknowledged",
                "created_at": (datetime.now() - timedelta(hours=25)).isoformat()
            }
        ]).encode())
        
        state_manager.redis.hset = AsyncMock(return_value=1)
        
        # Load current tasks
        current_tasks = await state_manager.load_active_tasks()
        
        # Simulate cleanup logic (remove old completed tasks, mark stale tasks)
        cleaned_tasks = []
        now = datetime.now()
        
        for task in current_tasks:
            if task["status"] == "completed":
                # Check if it's old
                completed_at = datetime.fromisoformat(task.get("completed_at", task.get("created_at")))
                if (now - completed_at).days < 1:  # Keep recent completions
                    cleaned_tasks.append(task)
            elif task["status"] in ["acknowledged", "in_progress"]:
                # Check if stale
                created_at = datetime.fromisoformat(task["created_at"])
                if (now - created_at).total_seconds() > 24 * 3600:  # Mark as stale
                    task["status"] = "stale"
                cleaned_tasks.append(task)
        
        # Save cleaned tasks
        await state_manager.save_active_tasks(cleaned_tasks)
        
        # Verify cleanup happened
        assert len(cleaned_tasks) == 2  # Removed old completed task
        stale_task = next(t for t in cleaned_tasks if t["task_id"] == "stale_task")
        assert stale_task["status"] == "stale"