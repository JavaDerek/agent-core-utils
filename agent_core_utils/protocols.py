"""Protocol data structures for agent communication."""

from pydantic import BaseModel, validator, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class DelegationTask(BaseModel):
    """Standardized task structure for agent delegation."""
    
    # Core identification
    id: str = Field(..., description="Unique task identifier")
    thread_id: str = Field(..., description="Thread identifier for tracking")
    
    # Task details
    description: str = Field(..., description="Human-readable task description")
    priority: int = Field(..., ge=1, le=10, description="Priority 1-10, higher = more urgent")
    timeline: str = Field(..., description="Timeline: immediate, short_term, long_term")
    assigned_to: str = Field(..., description="Target agent name")
    
    # Success criteria
    success_metrics: List[str] = Field(..., description="How to measure success")
    estimated_impact: float = Field(..., ge=0.0, le=1.0, description="Expected business impact 0.0-1.0")
    estimated_effort: float = Field(..., ge=0.0, le=1.0, description="Expected effort required 0.0-1.0")
    
    # Optional metadata
    dependencies: List[str] = Field(default_factory=list, description="Other task IDs this depends on")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context data")
    
    # Timestamps
    created_at: datetime = Field(..., description="Task creation timestamp")
    deadline: Optional[datetime] = Field(None, description="Task deadline")

    @validator('timeline')
    def validate_timeline(cls, v):
        """Validate timeline values."""
        valid_timelines = ['immediate', 'short_term', 'long_term']
        if v not in valid_timelines:
            raise ValueError(f'Timeline must be one of: {valid_timelines}')
        return v

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskResponse(BaseModel):
    """Standardized response structure for task updates."""
    
    # Identification (must match original task)
    task_id: str = Field(..., description="Original task.id")
    thread_id: str = Field(..., description="Original task.thread_id")
    
    # Status information
    status: str = Field(..., description="acknowledged, in_progress, completed, failed")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    message: str = Field(..., description="Human-readable status message")
    
    # Optional response data
    results: Optional[Dict[str, Any]] = Field(default=None, description="Results for completed tasks")
    error: Optional[Dict[str, Any]] = Field(default=None, description="Error details for failed tasks")
    progress: Optional[Dict[str, Any]] = Field(default=None, description="Progress details for in_progress tasks")
    
    # Retry information (for failed tasks)
    retry_possible: Optional[bool] = Field(default=None, description="Whether task can be retried")
    retry_after: Optional[datetime] = Field(default=None, description="When to retry if applicable")

    @validator('status')
    def validate_status(cls, v):
        """Validate status values."""
        valid_statuses = ['acknowledged', 'in_progress', 'completed', 'failed']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {valid_statuses}')
        return v

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskError(BaseModel):
    """Standardized error structure."""
    
    error_code: str = Field(..., description="Machine-readable error code")
    error_message: str = Field(..., description="Human-readable error message")
    retry_possible: bool = Field(default=False, description="Whether task can be retried")
    retry_after: Optional[datetime] = Field(None, description="When to retry if applicable")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional error context")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskProgress(BaseModel):
    """Progress information for long-running tasks."""
    
    current_step: str = Field(..., description="What is currently being done")
    steps_completed: int = Field(..., ge=0, description="Number of steps finished")
    total_steps: Optional[int] = Field(None, ge=1, description="Total steps if known")
    estimated_completion: Optional[datetime] = Field(None, description="When task should finish")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional progress details")

    @validator('total_steps')
    def validate_total_steps(cls, v, values):
        """Validate that total_steps is greater than steps_completed."""
        if v is not None and 'steps_completed' in values:
            if v < values['steps_completed']:
                raise ValueError('total_steps must be >= steps_completed')
        return v

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }