"""Redis Streams management for agent communication."""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class RedisStreamManager:
    """Low-level Redis Streams operations for agent communication."""
    
    def __init__(self, redis_client):
        """Initialize with Redis client.
        
        Args:
            redis_client: AsyncIO Redis client instance
        """
        self.redis = redis_client
    
    async def send_message(
        self, 
        stream_name: str, 
        data: Dict[str, Any], 
        max_length: int = 10000,
        max_retries: int = 3
    ) -> str:
        """Send a message to a Redis stream.
        
        Args:
            stream_name: Name of the stream
            data: Message data
            max_length: Maximum stream length (for trimming)
            max_retries: Maximum number of retry attempts
            
        Returns:
            Message ID
        """
        # Serialize complex data to JSON strings
        serialized_data = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                serialized_data[key] = json.dumps(value, default=self._json_serializer)
            elif isinstance(value, datetime):
                serialized_data[key] = value.isoformat()
            else:
                serialized_data[key] = str(value)
        
        # Send to Redis stream with retry logic
        for attempt in range(max_retries + 1):
            try:
                message_id = await self.redis.xadd(
                    stream_name,
                    serialized_data,
                    maxlen=max_length,
                    approximate=True
                )
                
                # Convert bytes to string if needed
                if isinstance(message_id, bytes):
                    message_id = message_id.decode('utf-8')
                    
                return message_id
                
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Failed to send message (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Failed to send message after {max_retries + 1} attempts: {e}")
                    raise
    
    async def read_messages(
        self, 
        streams: Dict[str, str], 
        last_ids: Optional[Dict[str, str]] = None,
        block: int = 1000, 
        count: int = 100
    ) -> Dict[str, List[Tuple[str, Dict[str, Any]]]]:
        """Read messages from multiple streams.
        
        Args:
            streams: Dict of {stream_name: last_read_id}
            last_ids: Override last IDs for specific streams
            block: Milliseconds to block waiting for messages (0 = no block)
            count: Maximum messages to read per stream
            
        Returns:
            Dict of {stream_name: [(message_id, data), ...]}
        """
        # Use last_ids override if provided
        if last_ids:
            streams = {**streams, **last_ids}
        
        try:
            # Read from Redis streams
            response = await self.redis.xread(
                streams=streams,
                block=block,
                count=count
            )
            
            # Process response
            result = {}
            for stream_response in response:
                if isinstance(stream_response, (list, tuple)) and len(stream_response) == 2:
                    stream_name, messages = stream_response
                    
                    # Decode stream name
                    if isinstance(stream_name, bytes):
                        stream_name = stream_name.decode('utf-8')
                    
                    # Process messages
                    processed_messages = []
                    for message in messages:
                        if isinstance(message, (list, tuple)) and len(message) == 2:
                            msg_id, msg_data = message
                            
                            # Decode message ID
                            if isinstance(msg_id, bytes):
                                msg_id = msg_id.decode('utf-8')
                            
                            # Deserialize message data
                            deserialized_data = self._deserialize_message_data(msg_data)
                            processed_messages.append((msg_id, deserialized_data))
                    
                    result[stream_name] = processed_messages
            
            return result
            
        except Exception as e:
            # Let connection errors propagate
            raise e
    
    async def create_consumer_group(
        self, 
        stream_name: str, 
        group_name: str, 
        start_id: str = "0"
    ) -> bool:
        """Create consumer group for reliable processing.
        
        Args:
            stream_name: Stream to create group for
            group_name: Name of consumer group
            start_id: Starting message ID for group
            
        Returns:
            bool: True if created successfully
        """
        try:
            await self.redis.xgroup_create(
                stream_name, 
                group_name, 
                start_id, 
                mkstream=True
            )
            return True
        except Exception as e:
            # Handle "BUSYGROUP Consumer Group name already exists" error
            if "BUSYGROUP" in str(e):
                return True  # Group already exists, that's fine
            raise e
    
    async def read_consumer_group(
        self,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        count: int = 10
    ) -> Dict[str, List[Tuple[str, Dict[str, Any]]]]:
        """Read messages using consumer group.
        
        Args:
            stream_name: Stream to read from
            group_name: Consumer group name
            consumer_name: This consumer's name
            count: Maximum messages to read
            
        Returns:
            Dict of {stream_name: [(message_id, data), ...]}
        """
        response = await self.redis.xreadgroup(
            group_name,
            consumer_name,
            {stream_name: ">"},
            count=count
        )
        
        # Process response similar to read_messages
        result = {}
        for stream_response in response:
            if isinstance(stream_response, (list, tuple)) and len(stream_response) == 2:
                stream_name_bytes, messages = stream_response
                
                # Decode stream name
                if isinstance(stream_name_bytes, bytes):
                    stream_name_decoded = stream_name_bytes.decode('utf-8')
                else:
                    stream_name_decoded = stream_name_bytes
                
                # Process messages
                processed_messages = []
                for message in messages:
                    if isinstance(message, (list, tuple)) and len(message) == 2:
                        msg_id, msg_data = message
                        
                        # Decode message ID
                        if isinstance(msg_id, bytes):
                            msg_id = msg_id.decode('utf-8')
                        
                        # Deserialize message data
                        deserialized_data = self._deserialize_message_data(msg_data)
                        processed_messages.append((msg_id, deserialized_data))
                
                result[stream_name_decoded] = processed_messages
        
        return result
    
    async def ack_message(self, stream_name: str, group_name: str, message_id: str) -> int:
        """Acknowledge message processing.
        
        Args:
            stream_name: Stream name
            group_name: Consumer group name
            message_id: Message ID to acknowledge
            
        Returns:
            int: Number of messages acknowledged
        """
        return await self.redis.xack(stream_name, group_name, message_id)
    
    async def get_stream_info(self, stream_name: str) -> Dict[str, Any]:
        """Get stream metadata.
        
        Args:
            stream_name: Stream to get info for
            
        Returns:
            Dict with stream metadata
        """
        info = await self.redis.xinfo_stream(stream_name)
        
        # Convert bytes to strings and format response
        result = {}
        for key, value in info.items():
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            elif isinstance(value, list) and len(value) == 2:
                # Handle entry format [id, fields]
                entry_id, entry_fields = value
                if isinstance(entry_id, bytes):
                    entry_id = entry_id.decode('utf-8')
                result[key] = [entry_id, entry_fields]
                continue
            
            result[key] = value
        
        return result
    
    async def trim_stream(self, stream_name: str, max_length: int) -> int:
        """Remove old messages from stream.
        
        Args:
            stream_name: Stream to trim
            max_length: Maximum messages to keep
            
        Returns:
            int: Number of messages removed
        """
        return await self.redis.xtrim(
            stream_name, 
            maxlen=max_length, 
            approximate=True
        )
    
    def _deserialize_message_data(self, msg_data: Dict[bytes, bytes]) -> Dict[str, Any]:
        """Deserialize message data from Redis.
        
        Args:
            msg_data: Raw message data from Redis (bytes -> bytes)
            
        Returns:
            Deserialized message data
        """
        result = {}
        for key, value in msg_data.items():
            # Decode key
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            
            # Decode value
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            
            # Try to deserialize JSON strings
            if isinstance(value, str) and (
                value.startswith('{') or value.startswith('[')
            ):
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    result[key] = value
            else:
                result[key] = value
        
        return result
    
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