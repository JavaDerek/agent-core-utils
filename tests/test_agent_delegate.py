"""Tests for AgentDelegate class."""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from agent_core_utils.delegation import AgentDelegate


class TestAgentDelegate:
    """Test AgentDelegate class functionality."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        mock_redis = AsyncMock()
        return mock_redis

    @pytest.fixture
    def delegate(self, mock_redis_client):
        """Create an AgentDelegate instance with mock Redis client."""
        return AgentDelegate(mock_redis_client, "bear")

    @pytest.fixture
    def sample_task_data(self):
        """Create sample task data for testing."""
        return {
            "id": "test_task_1",
            "thread_id": "thread_123",
            "description": "Research European progressive rock festivals",
            "priority": 8,
            "timeline": "immediate",
            "assigned_to": "bear",
            "success_metrics": ["Find at least 5 festivals", "Secure booking at 1 major festival"],
            "estimated_impact": 0.8,
            "estimated_effort": 0.6,
            "created_at": datetime.now().isoformat()
        }

    def test_delegate_initialization(self, mock_redis_client):
        """Test AgentDelegate initialization."""
        delegate = AgentDelegate(mock_redis_client, "bear")
        
        assert delegate.redis_client == mock_redis_client
        assert delegate.agent_name == "bear"
        assert hasattr(delegate, 'running')
        assert hasattr(delegate, 'last_read_id')

    async def test_listen_for_tasks_basic(self, delegate, mock_redis_client):
        """Test basic task listening functionality."""
        # Mock Redis stream read response
        mock_task_data = [
            (
                b"bear:commands",
                [
                    (
                        b"1234567890-0",
                        {
                            b"task_id": b"test_task_1",
                            b"thread_id": b"thread_123",
                            b"description": b"Test task",
                            b"assigned_to": b"bear"
                        }
                    )
                ]
            )
        ]
        
        # Mock to return data once, then empty to stop listening
        mock_redis_client.xread = AsyncMock(side_effect=[mock_task_data, []])
        
        # Mock callback function
        callback = AsyncMock()
        
        # Start listening (will stop after second call returns empty)
        delegate.running = True
        
        # Run listen_for_tasks with timeout to prevent hanging
        try:
            await asyncio.wait_for(delegate.listen_for_tasks(callback), timeout=1.0)
        except asyncio.TimeoutError:
            delegate.running = False
        
        # Verify callback was called with task data
        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert call_args["task_id"] == "test_task_1"
        assert call_args["description"] == "Test task"

    async def test_listen_for_tasks_multiple_messages(self, delegate, mock_redis_client):
        """Test listening for multiple tasks in one batch."""
        # Mock Redis response with multiple tasks
        mock_task_data = [
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
        
        mock_redis_client.xread = AsyncMock(side_effect=[mock_task_data, []])
        callback = AsyncMock()
        
        delegate.running = True
        
        try:
            await asyncio.wait_for(delegate.listen_for_tasks(callback), timeout=1.0)
        except asyncio.TimeoutError:
            delegate.running = False
        
        # Verify callback was called twice
        assert callback.call_count == 2
        
        # Verify both tasks were processed
        call_args_list = [call[0][0] for call in callback.call_args_list]
        task_ids = [args["task_id"] for args in call_args_list]
        assert "task_1" in task_ids
        assert "task_2" in task_ids

    async def test_listen_for_tasks_redis_error_handling(self, delegate, mock_redis_client):
        """Test error handling during task listening."""
        # Mock Redis to raise exception then succeed
        mock_redis_client.xread = AsyncMock(side_effect=[
            Exception("Redis connection lost"),
            []  # Empty response to stop
        ])
        
        callback = AsyncMock()
        delegate.running = True
        
        # Should handle error gracefully and continue
        try:
            await asyncio.wait_for(delegate.listen_for_tasks(callback), timeout=1.0)
        except asyncio.TimeoutError:
            delegate.running = False
        
        # Should have attempted to read twice despite first error
        assert mock_redis_client.xread.call_count == 2

    async def test_listen_for_tasks_callback_error_handling(self, delegate, mock_redis_client):
        """Test error handling when callback function fails."""
        mock_task_data = [
            (
                b"bear:commands",
                [
                    (
                        b"1234567890-0",
                        {b"task_id": b"test_task"}
                    )
                ]
            )
        ]
        
        mock_redis_client.xread = AsyncMock(side_effect=[mock_task_data, []])
        
        # Mock callback to raise exception
        callback = AsyncMock(side_effect=Exception("Callback failed"))
        delegate.running = True
        
        # Should handle callback error and continue
        try:
            await asyncio.wait_for(delegate.listen_for_tasks(callback), timeout=1.0)
        except asyncio.TimeoutError:
            delegate.running = False
        
        # Callback should have been called despite error
        callback.assert_called_once()

    async def test_send_task_response_basic(self, delegate, mock_redis_client):
        """Test basic task response sending."""
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        response_data = {
            "task_id": "test_task_1",
            "thread_id": "thread_123",
            "status": "acknowledged",
            "timestamp": datetime.now().isoformat(),
            "message": "Task received and queued"
        }
        
        await delegate.send_task_response("colonel", response_data)
        
        # Verify Redis xadd was called correctly
        mock_redis_client.xadd.assert_called_once()
        call_args = mock_redis_client.xadd.call_args
        
        # Check stream name
        assert call_args[0][0] == "responses:colonel"
        
        # Check response data
        sent_data = call_args[0][1]
        assert sent_data["task_id"] == "test_task_1"
        assert sent_data["status"] == "acknowledged"

    async def test_send_task_response_with_results(self, delegate, mock_redis_client):
        """Test sending task response with results data."""
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        results_data = {
            "festivals_found": 8,
            "bookings_secured": 2,
            "total_budget": 15000
        }
        
        response_data = {
            "task_id": "test_task_1",
            "thread_id": "thread_123",
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "message": "Task completed successfully",
            "results": results_data
        }
        
        await delegate.send_task_response("colonel", response_data)
        
        # Verify results were serialized correctly
        call_args = mock_redis_client.xadd.call_args
        sent_data = call_args[0][1]
        
        import json
        assert "results" in sent_data
        parsed_results = json.loads(sent_data["results"])
        assert parsed_results["festivals_found"] == 8

    async def test_acknowledge_task(self, delegate, mock_redis_client):
        """Test task acknowledgment convenience method."""
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        await delegate.acknowledge_task(
            "test_task_1",
            "thread_123",
            "colonel",
            "Task received and queued for processing"
        )
        
        # Verify acknowledgment was sent
        mock_redis_client.xadd.assert_called_once()
        call_args = mock_redis_client.xadd.call_args
        
        assert call_args[0][0] == "responses:colonel"
        sent_data = call_args[0][1]
        assert sent_data["status"] == "acknowledged"
        assert sent_data["task_id"] == "test_task_1"
        assert sent_data["thread_id"] == "thread_123"
        assert "Task received" in sent_data["message"]

    async def test_update_task_progress(self, delegate, mock_redis_client):
        """Test task progress update convenience method."""
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        progress_data = {
            "current_step": "Analyzing festival data",
            "steps_completed": 3,
            "total_steps": 8,
            "estimated_completion": (datetime.now() + timedelta(hours=2)).isoformat()
        }
        
        await delegate.update_task_progress(
            "test_task_1",
            "thread_123",
            "colonel",
            "Making good progress on festival research",
            progress_data
        )
        
        # Verify progress update was sent
        call_args = mock_redis_client.xadd.call_args
        sent_data = call_args[0][1]
        
        assert sent_data["status"] == "in_progress"
        assert "progress" in sent_data
        
        import json
        parsed_progress = json.loads(sent_data["progress"])
        assert parsed_progress["current_step"] == "Analyzing festival data"
        assert parsed_progress["steps_completed"] == 3

    async def test_complete_task(self, delegate, mock_redis_client):
        """Test task completion convenience method."""
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        results = {
            "festivals_found": 12,
            "major_bookings": 3,
            "budget_used": 8500,
            "recommendations": ["Download Festival", "Rock am Ring", "Hellfest"]
        }
        
        await delegate.complete_task(
            "test_task_1",
            "thread_123",
            "colonel",
            "Successfully completed festival research and secured bookings",
            results
        )
        
        # Verify completion was sent
        call_args = mock_redis_client.xadd.call_args
        sent_data = call_args[0][1]
        
        assert sent_data["status"] == "completed"
        assert "results" in sent_data
        
        import json
        parsed_results = json.loads(sent_data["results"])
        assert parsed_results["festivals_found"] == 12
        assert "Download Festival" in parsed_results["recommendations"]

    async def test_fail_task(self, delegate, mock_redis_client):
        """Test task failure convenience method."""
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        error_data = {
            "error_code": "API_TIMEOUT",
            "error_message": "Festival API timed out after 30 seconds",
            "retry_possible": True,
            "retry_after": (datetime.now() + timedelta(minutes=15)).isoformat(),
            "context": {"endpoint": "/api/festivals", "timeout": 30}
        }
        
        await delegate.fail_task(
            "test_task_1",
            "thread_123",
            "colonel",
            "Task failed due to API timeout, retry recommended",
            error_data
        )
        
        # Verify failure was sent
        call_args = mock_redis_client.xadd.call_args
        sent_data = call_args[0][1]
        
        assert sent_data["status"] == "failed"
        assert "error" in sent_data
        
        import json
        parsed_error = json.loads(sent_data["error"])
        assert parsed_error["error_code"] == "API_TIMEOUT"
        assert parsed_error["retry_possible"] is True

    async def test_task_response_timestamp_generation(self, delegate, mock_redis_client):
        """Test that timestamps are automatically generated for responses."""
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        before_time = datetime.now()
        
        await delegate.acknowledge_task("task_1", "thread_1", "colonel")
        
        after_time = datetime.now()
        
        # Verify timestamp was added
        call_args = mock_redis_client.xadd.call_args
        sent_data = call_args[0][1]
        
        assert "timestamp" in sent_data
        
        # Parse timestamp and verify it's within reasonable range
        timestamp = datetime.fromisoformat(sent_data["timestamp"].replace('Z', '+00:00') if sent_data["timestamp"].endswith('Z') else sent_data["timestamp"])
        assert before_time <= timestamp <= after_time

    async def test_multiple_source_agents(self, delegate, mock_redis_client):
        """Test sending responses to multiple source agents."""
        mock_redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        # Send responses to different agents
        await delegate.acknowledge_task("task_1", "thread_1", "colonel")
        await delegate.acknowledge_task("task_2", "thread_2", "sergeant")
        
        # Verify different response streams were used
        assert mock_redis_client.xadd.call_count == 2
        
        calls = mock_redis_client.xadd.call_args_list
        stream_names = [call[0][0] for call in calls]
        assert "responses:colonel" in stream_names
        assert "responses:sergeant" in stream_names

    async def test_task_data_deserialization(self, delegate, mock_redis_client):
        """Test proper deserialization of complex task data."""
        # Mock complex task data from Redis
        complex_context = {
            "source_agent": "colonel",
            "priority_factors": ["urgency", "impact"],
            "constraints": {"budget": 10000}
        }
        
        mock_task_data = [
            (
                b"bear:commands",
                [
                    (
                        b"1234567890-0",
                        {
                            b"task_id": b"complex_task",
                            b"description": b"Complex task with nested data",
                            b"context": json.dumps(complex_context).encode(),
                            b"success_metrics": json.dumps(["metric1", "metric2"]).encode()
                        }
                    )
                ]
            )
        ]
        
        mock_redis_client.xread = AsyncMock(side_effect=[mock_task_data, []])
        callback = AsyncMock()
        
        delegate.running = True
        
        try:
            await asyncio.wait_for(delegate.listen_for_tasks(callback), timeout=1.0)
        except asyncio.TimeoutError:
            delegate.running = False
        
        # Verify complex data was properly deserialized
        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        
        assert call_args["task_id"] == "complex_task"
        assert call_args["context"]["source_agent"] == "colonel"
        assert call_args["context"]["constraints"]["budget"] == 10000
        assert call_args["success_metrics"] == ["metric1", "metric2"]

    async def test_graceful_shutdown(self, delegate, mock_redis_client):
        """Test graceful shutdown of task listener."""
        # Mock Redis to keep returning data
        mock_task_data = [
            (
                b"bear:commands",
                [
                    (
                        b"1234567890-0",
                        {b"task_id": b"task_1"}
                    )
                ]
            )
        ]
        
        mock_redis_client.xread = AsyncMock(return_value=mock_task_data)
        callback = AsyncMock()
        
        # Start listening
        delegate.running = True
        
        # Create task to run listener
        listen_task = asyncio.create_task(delegate.listen_for_tasks(callback))
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        # Signal shutdown
        delegate.running = False
        
        # Wait for graceful shutdown
        try:
            await asyncio.wait_for(listen_task, timeout=1.0)
        except asyncio.TimeoutError:
            listen_task.cancel()
        
        # Should have processed at least one task
        assert callback.call_count >= 1

    async def test_redis_stream_position_tracking(self, delegate, mock_redis_client):
        """Test that stream position is properly tracked."""
        mock_task_data = [
            (
                b"bear:commands",
                [
                    (
                        b"1234567890-0",
                        {b"task_id": b"task_1"}
                    )
                ]
            )
        ]
        
        mock_redis_client.xread = AsyncMock(side_effect=[mock_task_data, []])
        callback = AsyncMock()
        
        # Initial position should be default
        initial_position = delegate.last_read_id
        
        delegate.running = True
        
        try:
            await asyncio.wait_for(delegate.listen_for_tasks(callback), timeout=1.0)
        except asyncio.TimeoutError:
            delegate.running = False
        
        # Position should be updated
        assert delegate.last_read_id != initial_position
        assert delegate.last_read_id == "1234567890-0"


class TestAgentDelegateIntegration:
    """Integration tests for AgentDelegate with realistic scenarios."""

    @pytest.fixture
    def delegate(self):
        """Create delegate with realistic setup."""
        mock_redis = AsyncMock()
        return AgentDelegate(mock_redis, "bear")

    async def test_full_task_processing_workflow(self, delegate):
        """Test complete task processing from reception to completion."""
        # Mock incoming task
        task_data = {
            "id": "festival_research_1",
            "thread_id": "thread_festival_1",
            "description": "Research European progressive rock festivals",
            "priority": 8,
            "timeline": "immediate",
            "assigned_to": "bear",
            "success_metrics": ["Find 5+ festivals", "Secure 1+ booking"],
            "estimated_impact": 0.8,
            "estimated_effort": 0.6
        }
        
        # Mock Redis operations
        delegate.redis_client.xadd = AsyncMock(return_value=b"response_id")
        
        # Simulate the full workflow
        
        # 1. Acknowledge task
        await delegate.acknowledge_task(
            task_data["id"],
            task_data["thread_id"],
            "colonel",
            "Task received and analysis started"
        )
        
        # 2. Send progress update
        await delegate.update_task_progress(
            task_data["id"],
            task_data["thread_id"],
            "colonel",
            "Researching festival databases",
            {
                "current_step": "Database research",
                "steps_completed": 2,
                "total_steps": 6
            }
        )
        
        # 3. Send another progress update
        await delegate.update_task_progress(
            task_data["id"],
            task_data["thread_id"],
            "colonel",
            "Contacting festival organizers",
            {
                "current_step": "Outreach phase",
                "steps_completed": 4,
                "total_steps": 6
            }
        )
        
        # 4. Complete task
        await delegate.complete_task(
            task_data["id"],
            task_data["thread_id"],
            "colonel",
            "Successfully researched festivals and secured bookings",
            {
                "festivals_found": 12,
                "bookings_secured": 3,
                "total_cost": 25000,
                "festivals": [
                    {"name": "Download Festival", "status": "booked"},
                    {"name": "Rock am Ring", "status": "booked"},
                    {"name": "Hellfest", "status": "booked"}
                ]
            }
        )
        
        # Verify all responses were sent
        assert delegate.redis_client.xadd.call_count == 4
        
        # Verify response progression
        calls = delegate.redis_client.xadd.call_args_list
        statuses = [json.loads(call[0][1].get("status", "unknown")) if isinstance(call[0][1].get("status"), str) else call[0][1]["status"] for call in calls]
        
        assert "acknowledged" in statuses
        assert statuses.count("in_progress") == 2  # Two progress updates
        assert "completed" in statuses

    async def test_task_failure_with_retry_workflow(self, delegate):
        """Test task failure handling with retry information."""
        task_data = {
            "id": "failing_task_1",
            "thread_id": "thread_fail_1"
        }
        
        delegate.redis_client.xadd = AsyncMock(return_value=b"response_id")
        
        # 1. Acknowledge task
        await delegate.acknowledge_task(
            task_data["id"],
            task_data["thread_id"],
            "colonel"
        )
        
        # 2. Send progress
        await delegate.update_task_progress(
            task_data["id"],
            task_data["thread_id"],
            "colonel",
            "Attempting to connect to festival API"
        )
        
        # 3. Fail with retry information
        await delegate.fail_task(
            task_data["id"],
            task_data["thread_id"],
            "colonel",
            "API connection failed, but service is temporarily down",
            {
                "error_code": "SERVICE_UNAVAILABLE",
                "error_message": "Festival booking API is temporarily unavailable",
                "retry_possible": True,
                "retry_after": (datetime.now() + timedelta(minutes=30)).isoformat(),
                "context": {
                    "api_endpoint": "https://api.festivals.com/bookings",
                    "error_details": "503 Service Unavailable",
                    "last_success": "2025-09-24T08:30:00Z"
                }
            }
        )
        
        # Verify failure response includes retry information
        calls = delegate.redis_client.xadd.call_args_list
        failure_call = calls[-1]  # Last call should be failure
        
        sent_data = failure_call[0][1]
        assert sent_data["status"] == "failed"
        
        error_data = json.loads(sent_data["error"])
        assert error_data["retry_possible"] is True
        assert error_data["error_code"] == "SERVICE_UNAVAILABLE"
        assert "retry_after" in error_data

    async def test_concurrent_task_processing(self, delegate):
        """Test processing multiple tasks concurrently."""
        # Mock multiple incoming tasks
        tasks = [
            {"id": f"task_{i}", "thread_id": f"thread_{i}"}
            for i in range(3)
        ]
        
        delegate.redis_client.xadd = AsyncMock(return_value=b"response_id")
        
        # Process all tasks concurrently
        acknowledgment_tasks = [
            delegate.acknowledge_task(task["id"], task["thread_id"], "colonel")
            for task in tasks
        ]
        
        await asyncio.gather(*acknowledgment_tasks)
        
        # Verify all acknowledgments were sent
        assert delegate.redis_client.xadd.call_count == 3
        
        # Verify all tasks were acknowledged
        calls = delegate.redis_client.xadd.call_args_list
        task_ids = [call[0][1]["task_id"] for call in calls]
        expected_ids = ["task_0", "task_1", "task_2"]
        
        for expected_id in expected_ids:
            assert expected_id in task_ids

    async def test_error_handling_during_response_sending(self, delegate):
        """Test error handling when response sending fails."""
        # Mock Redis to fail
        delegate.redis_client.xadd = AsyncMock(side_effect=Exception("Redis connection lost"))
        
        # Should handle Redis errors gracefully
        try:
            await delegate.acknowledge_task("task_1", "thread_1", "colonel")
        except Exception as e:
            # Should re-raise the exception for the caller to handle
            assert "Redis connection lost" in str(e)
        
        # Verify Redis was attempted
        delegate.redis_client.xadd.assert_called_once()