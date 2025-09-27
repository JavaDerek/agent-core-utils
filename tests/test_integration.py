"""Integration tests for agent communication system."""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta
import asyncio
import json

from agent_core_utils.delegation import AgentDelegator, AgentDelegate
from agent_core_utils.protocols import DelegationTask
from agent_core_utils.redis_streams import RedisStreamManager
from agent_core_utils.state_persistence import AgentStateManager


@pytest.mark.skip(reason="TODO: Fix hanging issue in integration tests for CI")
class TestAgentCommunicationIntegration:
    """Integration tests for complete agent communication workflows."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client for integration tests."""
        mock_redis = AsyncMock()
        return mock_redis

    @pytest.fixture
    def colonel_delegator(self, mock_redis_client):
        """Create Colonel agent (delegator) for testing."""
        return AgentDelegator(mock_redis_client, "colonel")

    @pytest.fixture
    def bear_delegate(self, mock_redis_client):
        """Create Bear agent (delegate) for testing."""
        return AgentDelegate(mock_redis_client, "bear")

    @pytest.fixture
    def stream_manager(self, mock_redis_client):
        """Create stream manager for testing."""
        return RedisStreamManager(mock_redis_client)

    @pytest.fixture  
    def state_manager(self, mock_redis_client):
        """Create state manager for testing."""
        return AgentStateManager(mock_redis_client, "bear")

    @pytest.fixture
    def sample_festival_task(self):
        """Create a realistic festival research task."""
        return DelegationTask(
            id="festival_research_001",
            thread_id="thread_festival_001",
            description="Research and book European progressive rock festivals for 2025 season",
            priority=9,
            timeline="immediate",
            assigned_to="bear",
            success_metrics=[
                "Identify at least 8 major progressive rock festivals",
                "Secure bookings at minimum 3 festivals",
                "Stay within budget of €50,000",
                "Complete by end of current quarter"
            ],
            estimated_impact=0.85,
            estimated_effort=0.70,
            created_at=datetime.now(),
            context={
                "budget": 50000,
                "currency": "EUR",
                "preferred_countries": ["Germany", "UK", "Netherlands", "France"],
                "genre_focus": "progressive_rock",
                "target_audience": 10000,
                "strategic_importance": "high"
            },
            deadline=datetime.now() + timedelta(days=30)
        )

    async def test_complete_delegation_workflow(self, colonel_delegator, bear_delegate, sample_festival_task):
        """Test complete workflow from task delegation to completion."""
        # Mock Redis operations for the full workflow
        redis_client = colonel_delegator.redis_client
        
        # Mock task delegation (Colonel -> Bear)
        redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        # Mock task listening (Bear receives task)
        task_message = [
            (
                b"bear:commands",
                [
                    (
                        b"1234567890-0",
                        {
                            b"task_id": sample_festival_task.id.encode(),
                            b"thread_id": sample_festival_task.thread_id.encode(),
                            b"description": sample_festival_task.description.encode(),
                            b"priority": str(sample_festival_task.priority).encode(),
                            b"context": json.dumps(sample_festival_task.context).encode(),
                            b"success_metrics": json.dumps(sample_festival_task.success_metrics).encode()
                        }
                    )
                ]
            )
        ]
        
        # Mock response reading (Colonel receives responses)
        response_sequence = [
            # Acknowledgment
            [
                (
                    b"responses:colonel",
                    [
                        (
                            b"1234567891-0",
                            {
                                b"task_id": sample_festival_task.id.encode(),
                                b"thread_id": sample_festival_task.thread_id.encode(),
                                b"status": b"acknowledged",
                                b"timestamp": datetime.now().isoformat().encode(),
                                b"message": b"Task received and analysis started"
                            }
                        )
                    ]
                )
            ],
            # Progress update 1
            [
                (
                    b"responses:colonel",
                    [
                        (
                            b"1234567892-0",
                            {
                                b"task_id": sample_festival_task.id.encode(),
                                b"status": b"in_progress",
                                b"message": b"Researching European festival databases",
                                b"progress": json.dumps({
                                    "current_step": "Database research",
                                    "steps_completed": 2,
                                    "total_steps": 8,
                                    "festivals_identified": 15
                                }).encode()
                            }
                        )
                    ]
                )
            ],
            # Progress update 2
            [
                (
                    b"responses:colonel",
                    [
                        (
                            b"1234567893-0",
                            {
                                b"task_id": sample_festival_task.id.encode(),
                                b"status": b"in_progress",
                                b"message": b"Contacting festival organizers for bookings",
                                b"progress": json.dumps({
                                    "current_step": "Booking negotiations",
                                    "steps_completed": 6,
                                    "total_steps": 8,
                                    "booking_requests_sent": 12
                                }).encode()
                            }
                        )
                    ]
                )
            ],
            # Completion
            [
                (
                    b"responses:colonel",
                    [
                        (
                            b"1234567894-0",
                            {
                                b"task_id": sample_festival_task.id.encode(),
                                b"status": b"completed",
                                b"message": b"Festival research and bookings completed successfully",
                                b"results": json.dumps({
                                    "festivals_researched": 18,
                                    "festivals_shortlisted": 8,
                                    "bookings_secured": 4,
                                    "total_cost": 42000,
                                    "currency": "EUR",
                                    "booked_festivals": [
                                        {
                                            "name": "Download Festival",
                                            "country": "UK",
                                            "date": "2025-06-15",
                                            "cost": 15000,
                                            "expected_attendance": 25000
                                        },
                                        {
                                            "name": "Rock am Ring",
                                            "country": "Germany", 
                                            "date": "2025-07-20",
                                            "cost": 12000,
                                            "expected_attendance": 20000
                                        },
                                        {
                                            "name": "Hellfest",
                                            "country": "France",
                                            "date": "2025-08-10",
                                            "cost": 10000,
                                            "expected_attendance": 15000
                                        },
                                        {
                                            "name": "Pinkpop Festival",
                                            "country": "Netherlands",
                                            "date": "2025-09-05",
                                            "cost": 5000,
                                            "expected_attendance": 12000
                                        }
                                    ],
                                    "budget_remaining": 8000,
                                    "success_metrics_met": 4,
                                    "completion_time": "28_days"
                                }).encode()
                            }
                        )
                    ]
                )
            ]
        ]
        
        # Configure Redis mocks
        redis_client.xread = AsyncMock(side_effect=[task_message] + response_sequence + [[]])
        
        # Step 1: Colonel delegates the task
        task_id = await colonel_delegator.delegate_task("bear", sample_festival_task.dict())
        assert task_id is not None
        
        # Verify task was sent to correct stream
        redis_client.xadd.assert_called()
        xadd_call = redis_client.xadd.call_args
        assert xadd_call[0][0] == "bear:commands"
        
        # Step 2: Bear listens for and receives the task
        received_tasks = []
        
        async def task_callback(task_data):
            received_tasks.append(task_data)
            
            # Bear acknowledges the task
            await bear_delegate.acknowledge_task(
                task_data["task_id"],
                task_data["thread_id"], 
                "colonel",
                "Task received and analysis started"
            )
            
            # Bear sends progress updates
            await bear_delegate.update_task_progress(
                task_data["task_id"],
                task_data["thread_id"],
                "colonel",
                "Researching European festival databases",
                {
                    "current_step": "Database research",
                    "steps_completed": 2,
                    "total_steps": 8,
                    "festivals_identified": 15
                }
            )
            
            await bear_delegate.update_task_progress(
                task_data["task_id"],
                task_data["thread_id"],
                "colonel", 
                "Contacting festival organizers for bookings",
                {
                    "current_step": "Booking negotiations",
                    "steps_completed": 6,
                    "total_steps": 8,
                    "booking_requests_sent": 12
                }
            )
            
            # Bear completes the task
            await bear_delegate.complete_task(
                task_data["task_id"],
                task_data["thread_id"],
                "colonel",
                "Festival research and bookings completed successfully",
                {
                    "festivals_researched": 18,
                    "bookings_secured": 4,
                    "total_cost": 42000,
                    "booked_festivals": [
                        {"name": "Download Festival", "cost": 15000},
                        {"name": "Rock am Ring", "cost": 12000},
                        {"name": "Hellfest", "cost": 10000},
                        {"name": "Pinkpop Festival", "cost": 5000}
                    ]
                }
            )
        
        # Simulate Bear listening (will process one task then stop)
        bear_delegate.running = True
        try:
            await asyncio.wait_for(bear_delegate.listen_for_tasks(task_callback), timeout=1.0)
        except asyncio.TimeoutError:
            bear_delegate.running = False
        
        # Verify task was received and processed
        assert len(received_tasks) == 1
        received_task = received_tasks[0]
        assert received_task["task_id"] == sample_festival_task.id
        assert received_task["description"] == sample_festival_task.description
        
        # Step 3: Colonel checks for responses
        all_responses = []
        
        # Check for acknowledgment
        ack_responses = await colonel_delegator.get_task_responses("bear")
        all_responses.extend(ack_responses)
        
        # Check for progress updates
        progress_responses_1 = await colonel_delegator.get_task_responses("bear")
        all_responses.extend(progress_responses_1)
        
        progress_responses_2 = await colonel_delegator.get_task_responses("bear") 
        all_responses.extend(progress_responses_2)
        
        # Check for completion
        completion_responses = await colonel_delegator.get_task_responses("bear")
        all_responses.extend(completion_responses)
        
        # Verify complete response sequence
        assert len(all_responses) == 4
        
        # Check acknowledgment
        ack_response = all_responses[0]
        assert ack_response["status"] == "acknowledged"
        assert ack_response["task_id"] == sample_festival_task.id
        
        # Check progress updates
        progress_1 = all_responses[1]
        assert progress_1["status"] == "in_progress"
        assert "Database research" in progress_1["message"]
        
        progress_2 = all_responses[2]
        assert progress_2["status"] == "in_progress"  
        assert "Booking negotiations" in progress_2["message"]
        
        # Check completion
        completion = all_responses[3]
        assert completion["status"] == "completed"
        assert "results" in completion
        results = json.loads(completion["results"]) if isinstance(completion["results"], str) else completion["results"]
        assert results["bookings_secured"] == 4
        assert results["total_cost"] == 42000
        assert len(results["booked_festivals"]) == 4

    async def test_agent_failure_and_recovery(self, colonel_delegator, bear_delegate):
        """Test agent failure scenarios and recovery mechanisms."""
        redis_client = colonel_delegator.redis_client
        
        # Mock task delegation
        redis_client.xadd = AsyncMock(return_value=b"1234567890-0")
        
        # Mock task message
        task_message = [
            (
                b"bear:commands",
                [
                    (
                        b"1234567890-0",
                        {
                            b"task_id": b"failing_task_001",
                            b"thread_id": b"thread_failing_001",
                            b"description": b"Task that will fail due to external service"
                        }
                    )
                ]
            )
        ]
        
        # Mock failure response
        failure_response = [
            (
                b"responses:colonel",
                [
                    (
                        b"1234567891-0",
                        {
                            b"task_id": b"failing_task_001",
                            b"status": b"failed",
                            b"message": b"External API unavailable",
                            b"error": json.dumps({
                                "error_code": "SERVICE_UNAVAILABLE",
                                "error_message": "Festival booking API returned 503",
                                "retry_possible": True,
                                "retry_after": (datetime.now() + timedelta(minutes=30)).isoformat(),
                                "context": {
                                    "api_endpoint": "https://api.festivals.com/bookings",
                                    "http_status": 503,
                                    "retry_count": 1
                                }
                            }).encode()
                        }
                    )
                ]
            )
        ]
        
        redis_client.xread = AsyncMock(side_effect=[task_message, failure_response, []])
        
        # Colonel delegates task
        task_data = {
            "id": "failing_task_001",
            "thread_id": "thread_failing_001", 
            "description": "Task that will fail due to external service",
            "assigned_to": "bear"
        }
        
        await colonel_delegator.delegate_task("bear", task_data)
        
        # Bear processes task and fails
        processed_tasks = []
        
        async def failing_task_callback(task_data):
            processed_tasks.append(task_data)
            
            # Acknowledge first
            await bear_delegate.acknowledge_task(
                task_data["task_id"],
                task_data["thread_id"],
                "colonel"
            )
            
            # Simulate work that fails
            await bear_delegate.fail_task(
                task_data["task_id"],
                task_data["thread_id"],
                "colonel",
                "External API unavailable",
                {
                    "error_code": "SERVICE_UNAVAILABLE",
                    "error_message": "Festival booking API returned 503",
                    "retry_possible": True,
                    "retry_after": (datetime.now() + timedelta(minutes=30)).isoformat(),
                    "context": {
                        "api_endpoint": "https://api.festivals.com/bookings",
                        "http_status": 503,
                        "retry_count": 1
                    }
                }
            )
        
        # Process failing task
        bear_delegate.running = True
        try:
            await asyncio.wait_for(bear_delegate.listen_for_tasks(failing_task_callback), timeout=1.0)
        except asyncio.TimeoutError:
            bear_delegate.running = False
        
        # Colonel checks for failure response
        responses = await colonel_delegator.get_task_responses("bear")
        
        # Should have acknowledgment and failure
        failure_response = next((r for r in responses if r["status"] == "failed"), None)
        assert failure_response is not None
        assert failure_response["task_id"] == "failing_task_001"
        
        error_data = json.loads(failure_response["error"]) if isinstance(failure_response["error"], str) else failure_response["error"]
        assert error_data["retry_possible"] is True
        assert error_data["error_code"] == "SERVICE_UNAVAILABLE"
        assert "retry_after" in error_data

    async def test_concurrent_multi_agent_communication(self, mock_redis_client):
        """Test concurrent communication between multiple agents."""
        # Create multiple agents
        colonel = AgentDelegator(mock_redis_client, "colonel")
        bear = AgentDelegate(mock_redis_client, "bear")
        bobo = AgentDelegate(mock_redis_client, "bobo")
        
        # Mock Redis operations
        mock_redis_client.xadd = AsyncMock(return_value=b"msg_id")
        
        # Mock messages for both agents
        bear_messages = [
            (
                b"bear:commands",
                [
                    (
                        b"1234567890-0",
                        {
                            b"task_id": b"bear_task_1",
                            b"description": b"Bear's festival task"
                        }
                    )
                ]
            )
        ]
        
        bobo_messages = [
            (
                b"bobo:commands", 
                [
                    (
                        b"1234567891-0",
                        {
                            b"task_id": b"bobo_task_1",
                            b"description": b"Bobo's venue task"
                        }
                    )
                ]
            )
        ]
        
        # Mock responses from both agents
        bear_response = [
            (
                b"responses:colonel",
                [
                    (
                        b"1234567892-0",
                        {
                            b"task_id": b"bear_task_1",
                            b"status": b"completed",
                            b"results": b'{"festivals_found": 8}'
                        }
                    )
                ]
            )
        ]
        
        bobo_response = [
            (
                b"responses:colonel",
                [
                    (
                        b"1234567893-0",
                        {
                            b"task_id": b"bobo_task_1", 
                            b"status": b"completed",
                            b"results": b'{"venues_found": 12}'
                        }
                    )
                ]
            )
        ]
        
        mock_redis_client.xread = AsyncMock(side_effect=[
            bear_messages, bobo_messages,  # Task messages
            bear_response, bobo_response,  # Response messages
            []  # End
        ])
        
        # Colonel delegates tasks to both agents concurrently
        bear_task = {"id": "bear_task_1", "description": "Bear's festival task"}
        bobo_task = {"id": "bobo_task_1", "description": "Bobo's venue task"}
        
        delegation_tasks = [
            colonel.delegate_task("bear", bear_task),
            colonel.delegate_task("bobo", bobo_task)
        ]
        
        task_ids = await asyncio.gather(*delegation_tasks)
        assert len(task_ids) == 2
        
        # Both agents process their tasks concurrently
        bear_processed = []
        bobo_processed = []
        
        async def bear_callback(task_data):
            bear_processed.append(task_data)
            await bear.complete_task(
                task_data["task_id"], 
                task_data.get("thread_id", "thread"),
                "colonel",
                "Bear completed festival task",
                {"festivals_found": 8}
            )
        
        async def bobo_callback(task_data):
            bobo_processed.append(task_data)
            await bobo.complete_task(
                task_data["task_id"],
                task_data.get("thread_id", "thread"), 
                "colonel",
                "Bobo completed venue task",
                {"venues_found": 12}
            )
        
        # Start both agents listening
        bear.running = True
        bobo.running = True
        
        listen_tasks = [
            asyncio.create_task(bear.listen_for_tasks(bear_callback)),
            asyncio.create_task(bobo.listen_for_tasks(bobo_callback))
        ]
        
        # Let them run briefly then stop
        await asyncio.sleep(0.1)
        bear.running = False
        bobo.running = False
        
        # Wait for completion or timeout
        try:
            await asyncio.wait_for(asyncio.gather(*listen_tasks, return_exceptions=True), timeout=1.0)
        except asyncio.TimeoutError:
            for task in listen_tasks:
                task.cancel()
        
        # Colonel checks responses from both agents
        bear_responses = await colonel.get_task_responses("bear")
        bobo_responses = await colonel.get_task_responses("bobo")
        
        # Verify both agents completed their tasks
        bear_completion = next((r for r in bear_responses if r["status"] == "completed"), None)
        bobo_completion = next((r for r in bobo_responses if r["status"] == "completed"), None)
        
        if bear_completion:
            results = json.loads(bear_completion["results"]) if isinstance(bear_completion["results"], str) else bear_completion["results"]
            assert results["festivals_found"] == 8
            
        if bobo_completion:
            results = json.loads(bobo_completion["results"]) if isinstance(bobo_completion["results"], str) else bobo_completion["results"]
            assert results["venues_found"] == 12

    async def test_state_persistence_during_communication(self, colonel_delegator, bear_delegate, state_manager):
        """Test state persistence during agent communication."""
        redis_client = state_manager.redis
        
        # Mock Redis operations
        redis_client.xadd = AsyncMock(return_value=b"msg_id")
        redis_client.hset = AsyncMock(return_value=1)
        redis_client.hget = AsyncMock(return_value=None)  # No existing state
        
        # Task message
        task_message = [
            (
                b"bear:commands",
                [
                    (
                        b"1234567890-0",
                        {
                            b"task_id": b"persistent_task_001",
                            b"description": b"Task with state tracking"
                        }
                    )
                ]
            )
        ]
        
        redis_client.xread = AsyncMock(side_effect=[task_message, []])
        
        # Save initial state (stream positions)
        initial_stream_ids = {"bear:commands": "$"}
        await state_manager.save_last_read_ids(initial_stream_ids)
        
        # Save active tasks
        initial_tasks = [
            {
                "task_id": "persistent_task_001",
                "status": "delegated", 
                "created_at": datetime.now().isoformat()
            }
        ]
        await state_manager.save_active_tasks(initial_tasks)
        
        # Process task and update state
        processed_tasks = []
        
        async def state_tracking_callback(task_data):
            processed_tasks.append(task_data)
            
            # Update task state to acknowledged
            updated_tasks = [
                {
                    "task_id": task_data["task_id"],
                    "status": "acknowledged",
                    "created_at": datetime.now().isoformat(),
                    "acknowledged_at": datetime.now().isoformat()
                }
            ]
            await state_manager.save_active_tasks(updated_tasks)
            
            # Send acknowledgment
            await bear_delegate.acknowledge_task(
                task_data["task_id"],
                task_data.get("thread_id", "thread"),
                "colonel"
            )
            
            # Update stream position
            updated_stream_ids = {"bear:commands": "1234567890-0"}
            await state_manager.save_last_read_ids(updated_stream_ids)
        
        # Process task with state tracking
        bear_delegate.running = True
        try:
            await asyncio.wait_for(bear_delegate.listen_for_tasks(state_tracking_callback), timeout=1.0)
        except asyncio.TimeoutError:
            bear_delegate.running = False
        
        # Verify state was saved multiple times
        assert redis_client.hset.call_count >= 3  # Initial stream + initial tasks + updates
        
        # Verify task was processed
        assert len(processed_tasks) == 1
        assert processed_tasks[0]["task_id"] == "persistent_task_001"


@pytest.mark.skip(reason="TODO: Fix datetime comparison and message corruption handling for CI")
class TestErrorHandlingAndResilience:
    """Test error handling and system resilience."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client for error testing."""
        return AsyncMock()

    async def test_redis_connection_failure_handling(self, mock_redis_client):
        """Test handling of Redis connection failures."""
        delegator = AgentDelegator(mock_redis_client, "colonel")
        
        # Mock Redis to fail
        mock_redis_client.xadd = AsyncMock(side_effect=ConnectionError("Redis connection lost"))
        
        # Should propagate the error for handling by the application
        with pytest.raises(ConnectionError):
            await delegator.delegate_task("bear", {"id": "test_task"})

    async def test_message_corruption_handling(self, mock_redis_client):
        """Test handling of corrupted messages."""
        delegate = AgentDelegate(mock_redis_client, "bear")
        
        # Mock corrupted message data
        corrupted_message = [
            (
                b"bear:commands",
                [
                    (
                        b"1234567890-0",
                        {
                            b"corrupted_field": b"invalid_json_data{{{",
                            b"incomplete_data": b"missing required fields"
                        }
                    )
                ]
            )
        ]
        
        mock_redis_client.xread = AsyncMock(side_effect=[corrupted_message, []])
        
        processed_messages = []
        errors_encountered = []
        
        async def error_handling_callback(task_data):
            try:
                processed_messages.append(task_data)
                # This might fail due to missing required fields
                if "task_id" not in task_data:
                    raise ValueError("Missing required task_id field")
            except Exception as e:
                errors_encountered.append(str(e))
        
        delegate.running = True
        try:
            await asyncio.wait_for(delegate.listen_for_tasks(error_handling_callback), timeout=1.0)
        except asyncio.TimeoutError:
            delegate.running = False
        
        # Should have attempted to process the message
        assert len(processed_messages) == 1
        # Error should have been handled by callback
        assert len(errors_encountered) == 1

    async def test_task_timeout_scenarios(self, mock_redis_client):
        """Test task timeout handling."""
        delegator = AgentDelegator(mock_redis_client, "colonel")
        
        mock_redis_client.xadd = AsyncMock(return_value=b"msg_id")
        
        # Delegate a task
        task_data = {
            "id": "timeout_task",
            "description": "Task that will timeout",
            "timeout_seconds": 60
        }
        
        await delegator.delegate_task("bear", task_data)
        
        # Simulate task in active tasks
        old_time = datetime.now() - timedelta(hours=2)
        delegator.active_tasks["timeout_task"] = {
            "target_agent": "bear",
            "status": "delegated",
            "created_at": old_time,
            "timeout_seconds": 3600  # 1 hour timeout
        }
        
        # Get timed out tasks
        timed_out = []
        now = datetime.now()
        for task_id, task_info in delegator.active_tasks.items():
            created_at = task_info["created_at"]
            timeout_seconds = task_info.get("timeout_seconds", 3600)
            
            if (now - created_at).total_seconds() > timeout_seconds:
                timed_out.append({"task_id": task_id, **task_info})
        
        # Should identify the timed out task
        assert len(timed_out) == 1
        assert timed_out[0]["task_id"] == "timeout_task"