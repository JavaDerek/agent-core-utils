"""State persistence for agent communication system."""

import json
from typing import Dict, List, Any
from datetime import datetime


class AgentStateManager:
    """Persist agent state between restarts."""
    
    def __init__(self, redis_client, agent_name: str):
        """Initialize state manager.
        
        Args:
            redis_client: AsyncIO Redis client instance
            agent_name: Name of this agent (e.g., "bear")
        """
        self.redis = redis_client
        self.agent_name = agent_name
        self.state_key = f"agent_state:{agent_name}"
    
    async def save_last_read_ids(self, stream_ids: Dict[str, str]) -> None:
        """Save last read IDs for streams.
        
        Args:
            stream_ids: Dict of {stream_name: last_read_id}
        """
        serialized_ids = json.dumps(stream_ids, default=self._json_serializer)
        await self.redis.hset(
            self.state_key,
            mapping={"last_read_ids": serialized_ids}
        )
    
    async def load_last_read_ids(self) -> Dict[str, str]:
        """Load last read IDs for streams.
        
        Returns:
            Dict of {stream_name: last_read_id} or empty dict if none exist
        """
        try:
            data = await self.redis.hget(self.state_key, "last_read_ids")
            if data is None:
                return {}
            
            # Decode bytes if needed
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            
            return json.loads(data)
        except (json.JSONDecodeError, Exception):
            return {}
    
    async def save_active_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """Save currently active tasks.
        
        Args:
            tasks: List of active task dictionaries
        """
        serialized_tasks = json.dumps(tasks, default=self._json_serializer)
        await self.redis.hset(
            self.state_key,
            mapping={"active_tasks": serialized_tasks}
        )
    
    async def load_active_tasks(self) -> List[Dict[str, Any]]:
        """Load active tasks from previous session.
        
        Returns:
            List of active task dictionaries or empty list if none exist
        """
        try:
            data = await self.redis.hget(self.state_key, "active_tasks")
            if data is None:
                return []
            
            # Decode bytes if needed
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            
            return json.loads(data)
        except (json.JSONDecodeError, Exception):
            return []
    
    async def save_agent_metadata(self, metadata: Dict[str, Any]) -> None:
        """Save agent configuration and status.
        
        Args:
            metadata: Agent metadata dictionary
        """
        serialized_metadata = json.dumps(metadata, default=self._json_serializer)
        await self.redis.hset(
            self.state_key,
            mapping={"agent_metadata": serialized_metadata}
        )
    
    async def load_agent_metadata(self) -> Dict[str, Any]:
        """Load agent configuration and status.
        
        Returns:
            Agent metadata dictionary or empty dict if none exists
        """
        try:
            data = await self.redis.hget(self.state_key, "agent_metadata")
            if data is None:
                return {}
            
            # Decode bytes if needed
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            
            return json.loads(data)
        except (json.JSONDecodeError, Exception):
            return {}
    
    def _json_serializer(self, obj: Any) -> str:
        """Custom JSON serializer for complex objects.
        
        Args:
            obj: Object to serialize
            
        Returns:
            JSON-serializable representation
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        
        # For other types, convert to string
        return str(obj)