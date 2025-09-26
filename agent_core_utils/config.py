"""Configuration for agent communication system."""

from pydantic import BaseModel, Field, validator
from typing import Optional


class CommunicationConfig(BaseModel):
    """Configuration for agent communication system."""
    
    # Redis connection settings
    redis_host: str = Field(default="localhost", description="Redis server hostname")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis server port")
    redis_password: Optional[str] = Field(default=None, description="Redis password if required")
    
    # Stream settings
    stream_max_length: int = Field(default=10000, ge=1, description="Maximum messages per stream")
    read_block_timeout: int = Field(default=1000, ge=0, description="Milliseconds to block on read")
    read_batch_size: int = Field(default=100, ge=1, description="Messages per batch")
    
    # Retry settings
    max_retries: int = Field(default=3, ge=1, description="Maximum retry attempts")
    retry_backoff_factor: float = Field(default=2.0, gt=0.0, description="Exponential backoff factor")
    max_retry_delay: int = Field(default=300, ge=1, description="Maximum seconds between retries")
    
    # Task timeouts
    acknowledgment_timeout: int = Field(default=30, ge=1, description="Seconds to wait for ack")
    task_timeout: int = Field(default=3600, ge=1, description="Seconds before task is stale")
    
    # Cleanup settings
    cleanup_interval: int = Field(default=3600, ge=1, description="Seconds between cleanup runs")
    max_task_age: int = Field(default=86400, ge=1, description="Seconds to keep completed tasks")
    
    # Stream names
    delegation_stream: str = Field(default="agent:tasks", description="Stream for task delegation")
    response_stream: str = Field(default="agent:responses", description="Stream for task responses")
    
    # Communication delays  
    retry_delay: float = Field(default=1.0, ge=0.1, description="Seconds to wait between retries")

    @validator('redis_host')
    def validate_redis_host(cls, v):
        """Validate Redis host is not empty."""
        if not v or not v.strip():
            raise ValueError('Redis host cannot be empty')
        return v.strip()

    class Config:
        """Pydantic configuration."""
        validate_assignment = True