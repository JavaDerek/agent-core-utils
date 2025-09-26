"""Tests for AgentDelegator class."""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta

from agent_core_utils.delegation import AgentDelegator
from agent_core_utils.protocols import DelegationTask


class TestAgentDelegator:
    """Test AgentDelegator class functionality."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        mock_redis = AsyncMock()
        return mock_redis

    @pytest.fixture
    def delegator(self, mock_redis_client):
        """Create an AgentDelegator instance with mock Redis client."""
        return AgentDelegator(mock_redis_client, "colonel")

    @pytest.fixture
    def sample_task(self):
        """Create a sample DelegationTask for testing."""
        return DelegationTask(
            id="test_task_1",
            thread_id="thread_123",
            description="Research European progressive rock festivals",
            priority=8,
            timeline="immediate",
            assigned_to="bear",
            success_metrics=["Find at least 5 festivals", "Secure booking at 1 major festival"],
            estimated_impact=0.8,
            estimated_effort=0.6,
            created_at=datetime.now()
        )

    def test_delegator_initialization(self, mock_redis_client):
        """Test AgentDelegator initialization."""
        delegator = AgentDelegator(mock_redis_client, "colonel")
        
        assert delegator.redis_client == mock_redis_client
        assert delegator.source_agent_name == "colonel"
        assert hasattr(delegator, 'active_tasks')
        assert hasattr(delegator, 'last_read_ids')

    async def test_delegate_task_basic(self, delegator, mock_redis_client, sample_task):
        """Test basic task delegation."""
        # Mock Redis stream operations
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        task_id = await delegator.delegate_task("bear", sample_task.dict())
        
        # Verify task ID is returned
        assert isinstance(task_id, str)
        assert task_id.startswith("test_task_1")  # Should include original task ID
        
        # Verify Redis stream was called correctly
        mock_redis_client.xadd.assert_called_once()
        call_args = mock_redis_client.xadd.call_args
        
        # Check stream name
        assert call_args[0][0] == "bear:commands"  # Stream name
        
        # Check message data contains required fields
        message_data = call_args[0][1]
        assert "task_id" in message_data
        assert "thread_id" in message_data
        assert "description" in message_data
        assert "assigned_to" in message_data
        assert message_data["assigned_to"] == "bear"

    async def test_delegate_task_generates_unique_ids(self, delegator, mock_redis_client, sample_task):
        """Test that delegate_task generates unique task and thread IDs."""
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        # Delegate the same task twice
        task_id_1 = await delegator.delegate_task("bear", sample_task.dict())
        task_id_2 = await delegator.delegate_task("bear", sample_task.dict())
        
        # IDs should be different
        assert task_id_1 != task_id_2
        
        # Both should be called
        assert mock_redis_client.xadd.call_count == 2

    async def test_delegate_task_stores_for_tracking(self, delegator, mock_redis_client, sample_task):
        """Test that delegated tasks are stored for response tracking."""
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        task_id = await delegator.delegate_task("bear", sample_task.dict())
        
        # Verify task is stored in active_tasks
        assert task_id in delegator.active_tasks
        stored_task = delegator.active_tasks[task_id]
        assert stored_task["target_agent"] == "bear"
        assert stored_task["status"] == "delegated"
        assert "created_at" in stored_task

    async def test_delegate_task_redis_error_handling(self, delegator, mock_redis_client, sample_task):
        """Test error handling when Redis operations fail."""
        # Mock Redis to raise an exception
        mock_redis_client.xadd = AsyncMock(side_effect=Exception("Redis unavailable"))
        
        with pytest.raises(Exception) as exc_info:
            await delegator.delegate_task("bear", sample_task.dict())
        
        assert "Redis unavailable" in str(exc_info.value)

    async def test_get_task_responses_basic(self, delegator, mock_redis_client):
        """Test basic task response retrieval."""
        # Mock Redis stream read response
        mock_response_data = [
            (
                b"responses:colonel",
                [
                    (
                        b"1234567890-0",
                        {
                            b"task_id": b"test_task_1",
                            b"thread_id": b"thread_123",
                            b"status": b"acknowledged",
                            b"timestamp": b"2025-09-24T10:00:00",
                            b"message": b"Task received"
                        }
                    ),
                    (
                        b"1234567891-0",
                        {
                            b"task_id": b"test_task_1",
                            b"thread_id": b"thread_123",
                            b"status": b"completed",
                            b"timestamp": b"2025-09-24T11:00:00",
                            b"message": b"Task completed successfully",
                            b"results": b'{"festivals_found": 8}'
                        }
                    )
                ]
            )
        ]
        
        mock_redis_client.xread = AsyncMock(return_value=mock_response_data)
        
        responses = await delegator.get_task_responses("bear")
        
        # Verify responses are returned
        assert len(responses) == 2
        assert responses[0]["task_id"] == "test_task_1"
        assert responses[0]["status"] == "acknowledged"
        assert responses[1]["status"] == "completed"
        
        # Verify Redis was called correctly
        mock_redis_client.xread.assert_called_once()
        call_args = mock_redis_client.xread.call_args[1]
        assert "responses:colonel" in call_args["streams"]

    async def test_get_task_responses_empty(self, delegator, mock_redis_client):
        """Test task response retrieval when no responses are available."""
        # Mock empty Redis response
        mock_redis_client.xread = AsyncMock(return_value=[])
        
        responses = await delegator.get_task_responses("bear")
        
        assert responses == []

    async def test_get_task_responses_updates_last_read_id(self, delegator, mock_redis_client):
        """Test that get_task_responses updates the last read ID."""
        # Mock Redis response
        mock_response_data = [
            (
                b"responses:colonel",
                [
                    (
                        b"1234567890-0",
                        {
                            b"task_id": b"test_task_1",
                            b"status": b"acknowledged"
                        }
                    )
                ]
            )
        ]
        
        mock_redis_client.xread = AsyncMock(return_value=mock_response_data)
        
        # Initial last_read_id should be empty or default
        initial_id = delegator.last_read_ids.get("responses:colonel", "$")
        
        await delegator.get_task_responses("bear")
        
        # Last read ID should be updated
        updated_id = delegator.last_read_ids.get("responses:colonel")
        assert updated_id == "1234567890-0"
        assert updated_id != initial_id

    async def test_get_task_status_existing_task(self, delegator, mock_redis_client):
        """Test getting status of an existing task."""
        # Add a task to active_tasks
        task_id = "test_task_1"
        delegator.active_tasks[task_id] = {
            "target_agent": "bear",
            "status": "delegated",
            "created_at": datetime.now(),
            "last_response": None
        }
        
        status = await delegator.get_task_status(task_id)
        
        assert status is not None
        assert status["target_agent"] == "bear"
        assert status["status"] == "delegated"

    async def test_get_task_status_nonexistent_task(self, delegator, mock_redis_client):
        """Test getting status of a non-existent task."""
        status = await delegator.get_task_status("nonexistent_task")
        
        assert status is None

    def test_get_active_tasks_empty(self, delegator):
        """Test getting active tasks when none exist."""
        active_tasks = delegator.get_active_tasks()
        
        assert active_tasks == []

    def test_get_active_tasks_with_tasks(self, delegator):
        """Test getting active tasks when tasks exist."""
        # Add some tasks
        task1_data = {
            "target_agent": "bear",
            "status": "acknowledged",
            "created_at": datetime.now()
        }
        task2_data = {
            "target_agent": "bobo",
            "status": "in_progress",
            "created_at": datetime.now()
        }
        task3_data = {
            "target_agent": "bear",
            "status": "completed",
            "created_at": datetime.now()
        }
        
        delegator.active_tasks["task1"] = task1_data
        delegator.active_tasks["task2"] = task2_data
        delegator.active_tasks["task3"] = task3_data
        
        active_tasks = delegator.get_active_tasks()
        
        # Should only return acknowledged and in_progress tasks
        assert len(active_tasks) == 2
        task_ids = [task["task_id"] for task in active_tasks]
        assert "task1" in task_ids
        assert "task2" in task_ids
        assert "task3" not in task_ids  # Completed tasks should not be active

    async def test_task_response_processing_updates_status(self, delegator, mock_redis_client):
        """Test that processing task responses updates task status."""
        # Add a task to track
        task_id = "test_task_1"
        delegator.active_tasks[task_id] = {
            "target_agent": "bear",
            "status": "delegated",
            "created_at": datetime.now(),
            "last_response": None
        }
        
        # Mock Redis response with status update
        mock_response_data = [
            (
                b"responses:colonel",
                [
                    (
                        b"1234567890-0",
                        {
                            b"task_id": task_id.encode(),
                            b"thread_id": b"thread_123",
                            b"status": b"in_progress",
                            b"timestamp": b"2025-09-24T10:00:00",
                            b"message": b"Working on task"
                        }
                    )
                ]
            )
        ]
        
        mock_redis_client.xread = AsyncMock(return_value=mock_response_data)
        
        await delegator.get_task_responses("bear")
        
        # Verify task status was updated
        assert delegator.active_tasks[task_id]["status"] == "in_progress"
        assert delegator.active_tasks[task_id]["last_response"] is not None

    async def test_multiple_target_agents(self, delegator, mock_redis_client, sample_task):
        """Test delegating tasks to multiple target agents."""
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        # Delegate to different agents
        await delegator.delegate_task("bear", sample_task.dict())
        await delegator.delegate_task("bobo", sample_task.dict())
        
        # Verify different streams were used
        assert mock_redis_client.xadd.call_count == 2
        
        calls = mock_redis_client.xadd.call_args_list
        stream_names = [call[0][0] for call in calls]
        assert "bear:commands" in stream_names
        assert "bobo:commands" in stream_names

    async def test_task_timeout_handling(self, delegator, mock_redis_client):
        """Test handling of task timeouts."""
        # Add an old task that should be considered timed out
        old_time = datetime.now() - timedelta(hours=2)
        task_id = "old_task"
        delegator.active_tasks[task_id] = {
            "target_agent": "bear",
            "status": "delegated",
            "created_at": old_time,
            "last_response": None
        }
        
        # This should be implemented in the actual class
        timed_out_tasks = await delegator.get_timed_out_tasks(timeout_seconds=3600)
        
        assert len(timed_out_tasks) == 1
        assert timed_out_tasks[0]["task_id"] == task_id

    async def test_redis_connection_retry(self, delegator, mock_redis_client):
        """Test Redis connection retry logic."""
        # Mock Redis to fail first, then succeed
        mock_redis_client.xadd = AsyncMock(side_effect=[
            Exception("Connection lost"),
            b"1234567890-0"  # Success on retry
        ])
        
        sample_task = {
            "id": "test_task",
            "description": "Test task",
            "assigned_to": "bear"
        }
        
        # This should retry and eventually succeed
        task_id = await delegator.delegate_task("bear", sample_task)
        
        assert isinstance(task_id, str)
        assert mock_redis_client.xadd.call_count == 2

    async def test_message_serialization(self, delegator, mock_redis_client, sample_task):
        """Test that complex task data is properly serialized."""
        # Add complex nested data to task
        complex_task = sample_task.dict()
        complex_task["context"] = {
            "nested_data": {"key": "value"},
            "list_data": [1, 2, 3],
            "datetime_data": datetime.now().isoformat()
        }
        
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        await delegator.delegate_task("bear", complex_task)
        
        # Verify the call was made
        mock_redis_client.xadd.assert_called_once()
        
        # Verify complex data was serialized
        call_args = mock_redis_client.xadd.call_args
        message_data = call_args[0][1]
        
        # Context should be JSON serialized
        assert "context" in message_data
        import json
        context = json.loads(message_data["context"])
        assert context["nested_data"]["key"] == "value"
        assert context["list_data"] == [1, 2, 3]


class TestAgentDelegatorIntegration:
    """Integration tests for AgentDelegator with realistic scenarios."""

    @pytest.fixture
    def delegator(self):
        """Create delegator with real-ish setup."""
        mock_redis = AsyncMock()
        return AgentDelegator(mock_redis, "colonel")

    async def test_full_task_lifecycle(self, delegator):
        """Test a complete task lifecycle from delegation to completion."""
        # Mock Redis for all operations
        delegator.redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        # Mock response sequence: acknowledged -> in_progress -> completed
        response_sequence = [
            # First call - acknowledgment
            [
                (
                    b"responses:colonel",
                    [
                        (
                            b"1234567890-1",
                            {
                                b"task_id": b"festival_task_1",
                                b"status": b"acknowledged",
                                b"message": b"Task received"
                            }
                        )
                    ]
                )
            ],
            # Second call - progress
            [
                (
                    b"responses:colonel",
                    [
                        (
                            b"1234567890-2",
                            {
                                b"task_id": b"festival_task_1",
                                b"status": b"in_progress",
                                b"message": b"Researching festivals"
                            }
                        )
                    ]
                )
            ],
            # Third call - completion
            [
                (
                    b"responses:colonel",
                    [
                        (
                            b"1234567890-3",
                            {
                                b"task_id": b"festival_task_1",
                                b"status": b"completed",
                                b"message": b"Found 8 festivals",
                                b"results": b'{"festivals": 8, "bookings": 2}'
                            }
                        )
                    ]
                )
            ]
        ]
        
        delegator.redis_client.xread = AsyncMock(side_effect=response_sequence)
        
        # 1. Delegate task
        task_data = {
            "id": "festival_task_1",
            "description": "Research European festivals",
            "assigned_to": "bear"
        }
        
        task_id = await delegator.delegate_task("bear", task_data)
        assert task_id is not None
        
        # 2. Check for acknowledgment
        responses_1 = await delegator.get_task_responses("bear")
        assert len(responses_1) == 1
        assert responses_1[0]["status"] == "acknowledged"
        
        # 3. Check for progress
        responses_2 = await delegator.get_task_responses("bear")
        assert len(responses_2) == 1
        assert responses_2[0]["status"] == "in_progress"
        
        # 4. Check for completion
        responses_3 = await delegator.get_task_responses("bear")
        assert len(responses_3) == 1
        assert responses_3[0]["status"] == "completed"
        assert "results" in responses_3[0]

    async def test_concurrent_task_delegation(self, delegator):
        """Test delegating multiple tasks concurrently."""
        delegator.redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        # Create multiple tasks
        tasks = [
            {"id": f"task_{i}", "description": f"Task {i}", "assigned_to": "bear"}
            for i in range(5)
        ]
        
        # Delegate all tasks
        task_ids = []
        for task in tasks:
            task_id = await delegator.delegate_task("bear", task)
            task_ids.append(task_id)
        
        # Verify all tasks were delegated
        assert len(task_ids) == 5
        assert len(set(task_ids)) == 5  # All unique
        assert delegator.redis_client.xadd.call_count == 5

    async def test_error_recovery_and_retry(self, delegator):
        """Test error recovery and retry mechanisms."""
        # Mock Redis to fail then succeed
        delegator.redis_client.xadd = AsyncMock(side_effect=[
            Exception("Network error"),
            Exception("Redis timeout"),
            b"1234567890-0"  # Success
        ])
        
        task_data = {"id": "retry_task", "description": "Test retry", "assigned_to": "bear"}
        
        # Should eventually succeed after retries
        task_id = await delegator.delegate_task("bear", task_data)
        
        assert task_id is not None
        assert delegator.redis_client.xadd.call_count == 3