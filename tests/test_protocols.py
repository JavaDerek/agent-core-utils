"""Tests for agent communication protocol data structures."""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from agent_core_utils.protocols import (
    DelegationTask,
    TaskResponse,
    TaskError,
    TaskProgress,
)


class TestDelegationTask:
    """Test DelegationTask protocol data structure."""

    def test_delegation_task_creation_with_required_fields(self):
        """Test creating a DelegationTask with all required fields."""
        now = datetime.now()
        task = DelegationTask(
            id="test_task_1",
            thread_id="thread_123",
            description="Test task description",
            priority=5,
            timeline="short_term",
            assigned_to="bear",
            success_metrics=["Complete research", "Generate report"],
            estimated_impact=0.7,
            estimated_effort=0.5,
            created_at=now
        )
        
        assert task.id == "test_task_1"
        assert task.thread_id == "thread_123"
        assert task.description == "Test task description"
        assert task.priority == 5
        assert task.timeline == "short_term"
        assert task.assigned_to == "bear"
        assert task.success_metrics == ["Complete research", "Generate report"]
        assert task.estimated_impact == 0.7
        assert task.estimated_effort == 0.5
        assert task.created_at == now
        assert task.dependencies == []
        assert task.context is None
        assert task.deadline is None

    def test_delegation_task_creation_with_optional_fields(self):
        """Test creating a DelegationTask with optional fields."""
        now = datetime.now()
        deadline = now + timedelta(hours=24)
        
        task = DelegationTask(
            id="test_task_2",
            thread_id="thread_456",
            description="Complex task with dependencies",
            priority=8,
            timeline="immediate",
            assigned_to="bobo",
            success_metrics=["Achieve goal A", "Achieve goal B"],
            estimated_impact=0.9,
            estimated_effort=0.8,
            created_at=now,
            dependencies=["task_1", "task_2"],
            context={"source": "colonel", "urgent": True},
            deadline=deadline
        )
        
        assert task.dependencies == ["task_1", "task_2"]
        assert task.context == {"source": "colonel", "urgent": True}
        assert task.deadline == deadline

    def test_delegation_task_validation_priority_range(self):
        """Test that priority must be between 1-10."""
        now = datetime.now()
        
        # Test priority too low
        with pytest.raises(ValidationError):
            DelegationTask(
                id="test_task",
                thread_id="thread",
                description="Test",
                priority=0,  # Invalid: too low
                timeline="short_term",
                assigned_to="bear",
                success_metrics=["test"],
                estimated_impact=0.5,
                estimated_effort=0.5,
                created_at=now
            )
        
        # Test priority too high
        with pytest.raises(ValidationError):
            DelegationTask(
                id="test_task",
                thread_id="thread",
                description="Test",
                priority=11,  # Invalid: too high
                timeline="short_term",
                assigned_to="bear",
                success_metrics=["test"],
                estimated_impact=0.5,
                estimated_effort=0.5,
                created_at=now
            )

    def test_delegation_task_validation_impact_range(self):
        """Test that estimated_impact must be between 0.0-1.0."""
        now = datetime.now()
        
        with pytest.raises(ValidationError):
            DelegationTask(
                id="test_task",
                thread_id="thread",
                description="Test",
                priority=5,
                timeline="short_term",
                assigned_to="bear",
                success_metrics=["test"],
                estimated_impact=1.5,  # Invalid: too high
                estimated_effort=0.5,
                created_at=now
            )

    def test_delegation_task_validation_effort_range(self):
        """Test that estimated_effort must be between 0.0-1.0."""
        now = datetime.now()
        
        with pytest.raises(ValidationError):
            DelegationTask(
                id="test_task",
                thread_id="thread",
                description="Test",
                priority=5,
                timeline="short_term",
                assigned_to="bear",
                success_metrics=["test"],
                estimated_impact=0.5,
                estimated_effort=-0.1,  # Invalid: negative
                created_at=now
            )

    def test_delegation_task_serialization(self):
        """Test that DelegationTask can be serialized to/from dict."""
        now = datetime.now()
        task = DelegationTask(
            id="test_task",
            thread_id="thread",
            description="Test",
            priority=5,
            timeline="short_term",
            assigned_to="bear",
            success_metrics=["test"],
            estimated_impact=0.5,
            estimated_effort=0.5,
            created_at=now
        )
        
        # Test to dict
        task_dict = task.dict()
        assert isinstance(task_dict, dict)
        assert task_dict["id"] == "test_task"
        
        # Test from dict
        restored_task = DelegationTask(**task_dict)
        assert restored_task.id == task.id
        assert restored_task.created_at == task.created_at

    def test_delegation_task_json_serialization(self):
        """Test that DelegationTask can be serialized to/from JSON."""
        now = datetime.now()
        task = DelegationTask(
            id="test_task",
            thread_id="thread",
            description="Test",
            priority=5,
            timeline="short_term",
            assigned_to="bear",
            success_metrics=["test"],
            estimated_impact=0.5,
            estimated_effort=0.5,
            created_at=now
        )
        
        # Test to JSON
        task_json = task.json()
        assert isinstance(task_json, str)
        
        # Test from JSON
        restored_task = DelegationTask.parse_raw(task_json)
        assert restored_task.id == task.id


class TestTaskResponse:
    """Test TaskResponse protocol data structure."""

    def test_task_response_creation_acknowledged(self):
        """Test creating a TaskResponse for acknowledgment."""
        now = datetime.now()
        response = TaskResponse(
            task_id="test_task_1",
            thread_id="thread_123",
            status="acknowledged",
            timestamp=now,
            message="Task received and queued"
        )
        
        assert response.task_id == "test_task_1"
        assert response.thread_id == "thread_123"
        assert response.status == "acknowledged"
        assert response.timestamp == now
        assert response.message == "Task received and queued"
        assert response.results is None
        assert response.error is None
        assert response.progress is None

    def test_task_response_creation_in_progress(self):
        """Test creating a TaskResponse for progress update."""
        now = datetime.now()
        progress_data = {"current_step": "researching", "completion": 0.3}
        
        response = TaskResponse(
            task_id="test_task_1",
            thread_id="thread_123",
            status="in_progress",
            timestamp=now,
            message="Making progress on task",
            progress=progress_data
        )
        
        assert response.status == "in_progress"
        assert response.progress == progress_data

    def test_task_response_creation_completed(self):
        """Test creating a TaskResponse for task completion."""
        now = datetime.now()
        results_data = {"festivals_found": 5, "bookings_secured": 2}
        
        response = TaskResponse(
            task_id="test_task_1",
            thread_id="thread_123",
            status="completed",
            timestamp=now,
            message="Task completed successfully",
            results=results_data
        )
        
        assert response.status == "completed"
        assert response.results == results_data

    def test_task_response_creation_failed(self):
        """Test creating a TaskResponse for task failure."""
        now = datetime.now()
        retry_after = now + timedelta(minutes=30)
        error_data = {"error_code": "API_TIMEOUT", "details": "Service unavailable"}
        
        response = TaskResponse(
            task_id="test_task_1",
            thread_id="thread_123",
            status="failed",
            timestamp=now,
            message="Task failed due to API timeout",
            error=error_data,
            retry_possible=True,
            retry_after=retry_after
        )
        
        assert response.status == "failed"
        assert response.error == error_data
        assert response.retry_possible is True
        assert response.retry_after == retry_after

    def test_task_response_validation_status_values(self):
        """Test that status must be one of the allowed values."""
        now = datetime.now()
        
        # Valid statuses should work
        valid_statuses = ["acknowledged", "in_progress", "completed", "failed"]
        for status in valid_statuses:
            response = TaskResponse(
                task_id="test_task",
                thread_id="thread",
                status=status,
                timestamp=now,
                message="Test message"
            )
            assert response.status == status

    def test_task_response_serialization(self):
        """Test TaskResponse serialization."""
        now = datetime.now()
        response = TaskResponse(
            task_id="test_task",
            thread_id="thread",
            status="completed",
            timestamp=now,
            message="Done",
            results={"success": True}
        )
        
        # Test to dict
        response_dict = response.dict()
        assert isinstance(response_dict, dict)
        assert response_dict["task_id"] == "test_task"
        
        # Test from dict
        restored_response = TaskResponse(**response_dict)
        assert restored_response.task_id == response.task_id


class TestTaskError:
    """Test TaskError protocol data structure."""

    def test_task_error_creation_basic(self):
        """Test creating a basic TaskError."""
        error = TaskError(
            error_code="API_TIMEOUT",
            error_message="Request timed out after 30 seconds"
        )
        
        assert error.error_code == "API_TIMEOUT"
        assert error.error_message == "Request timed out after 30 seconds"
        assert error.retry_possible is False
        assert error.retry_after is None
        assert error.context is None

    def test_task_error_creation_with_retry(self):
        """Test creating a TaskError with retry information."""
        retry_time = datetime.now() + timedelta(minutes=15)
        context_data = {"endpoint": "/api/festivals", "timeout": 30}
        
        error = TaskError(
            error_code="RATE_LIMITED",
            error_message="API rate limit exceeded",
            retry_possible=True,
            retry_after=retry_time,
            context=context_data
        )
        
        assert error.error_code == "RATE_LIMITED"
        assert error.retry_possible is True
        assert error.retry_after == retry_time
        assert error.context == context_data

    def test_task_error_serialization(self):
        """Test TaskError serialization."""
        error = TaskError(
            error_code="VALIDATION_ERROR",
            error_message="Invalid input parameters"
        )
        
        error_dict = error.dict()
        assert isinstance(error_dict, dict)
        assert error_dict["error_code"] == "VALIDATION_ERROR"
        
        restored_error = TaskError(**error_dict)
        assert restored_error.error_code == error.error_code


class TestTaskProgress:
    """Test TaskProgress protocol data structure."""

    def test_task_progress_creation_basic(self):
        """Test creating basic TaskProgress."""
        progress = TaskProgress(
            current_step="Analyzing festival data",
            steps_completed=3
        )
        
        assert progress.current_step == "Analyzing festival data"
        assert progress.steps_completed == 3
        assert progress.total_steps is None
        assert progress.estimated_completion is None
        assert progress.details is None

    def test_task_progress_creation_detailed(self):
        """Test creating detailed TaskProgress."""
        completion_time = datetime.now() + timedelta(hours=2)
        details_data = {"festivals_processed": 15, "errors_encountered": 2}
        
        progress = TaskProgress(
            current_step="Processing festival bookings",
            steps_completed=7,
            total_steps=10,
            estimated_completion=completion_time,
            details=details_data
        )
        
        assert progress.current_step == "Processing festival bookings"
        assert progress.steps_completed == 7
        assert progress.total_steps == 10
        assert progress.estimated_completion == completion_time
        assert progress.details == details_data

    def test_task_progress_serialization(self):
        """Test TaskProgress serialization."""
        progress = TaskProgress(
            current_step="Final validation",
            steps_completed=9,
            total_steps=10
        )
        
        progress_dict = progress.dict()
        assert isinstance(progress_dict, dict)
        assert progress_dict["current_step"] == "Final validation"
        
        restored_progress = TaskProgress(**progress_dict)
        assert restored_progress.current_step == progress.current_step


class TestProtocolIntegration:
    """Test integration between protocol data structures."""

    def test_task_response_with_task_error(self):
        """Test TaskResponse containing TaskError."""
        now = datetime.now()
        error = TaskError(
            error_code="NETWORK_ERROR",
            error_message="Connection failed",
            retry_possible=True
        )
        
        response = TaskResponse(
            task_id="test_task",
            thread_id="thread",
            status="failed",
            timestamp=now,
            message="Task failed due to network error",
            error=error.dict()
        )
        
        assert response.status == "failed"
        assert response.error["error_code"] == "NETWORK_ERROR"
        assert response.error["retry_possible"] is True

    def test_task_response_with_task_progress(self):
        """Test TaskResponse containing TaskProgress."""
        now = datetime.now()
        progress = TaskProgress(
            current_step="Data collection",
            steps_completed=3,
            total_steps=8
        )
        
        response = TaskResponse(
            task_id="test_task",
            thread_id="thread",
            status="in_progress",
            timestamp=now,
            message="Task progressing well",
            progress=progress.dict()
        )
        
        assert response.status == "in_progress"
        assert response.progress["current_step"] == "Data collection"
        assert response.progress["steps_completed"] == 3

    def test_delegation_task_with_complex_context(self):
        """Test DelegationTask with complex context containing multiple data types."""
        now = datetime.now()
        complex_context = {
            "source_agent": "colonel",
            "priority_factors": ["urgency", "impact", "resources"],
            "constraints": {
                "budget": 10000,
                "timeline_days": 7,
                "required_approvals": ["manager", "finance"]
            },
            "metadata": {
                "created_by": "strategic_planner",
                "version": "1.2.0",
                "tags": ["festival", "booking", "europe"]
            }
        }
        
        task = DelegationTask(
            id="complex_task_1",
            thread_id="complex_thread",
            description="Complex festival booking with multiple constraints",
            priority=9,
            timeline="immediate",
            assigned_to="bear",
            success_metrics=["Secure booking", "Stay within budget", "Meet timeline"],
            estimated_impact=0.95,
            estimated_effort=0.85,
            created_at=now,
            context=complex_context
        )
        
        assert task.context["source_agent"] == "colonel"
        assert task.context["constraints"]["budget"] == 10000
        assert "festival" in task.context["metadata"]["tags"]