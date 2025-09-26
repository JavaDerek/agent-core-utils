"""Agent delegation and communication system."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Awaitable
from uuid import uuid4

from .protocols import DelegationTask, TaskResponse
from .config import CommunicationConfig
from .redis_streams import RedisStreamManager
from .state_persistence import AgentStateManager


logger = logging.getLogger(__name__)


class AgentDelegator:
    """Handle task delegation to Bear agent from Colonel."""
    
    def __init__(
        self,
        redis_client,
        agent_name: str = "colonel",
        config: Optional[CommunicationConfig] = None
    ):
        """Initialize the delegator.
        
        Args:
            redis_client: AsyncIO Redis client
            agent_name: Name of this agent (default: "colonel")
            config: Communication configuration (optional, will use defaults)
        """
        self.redis_client = redis_client  # For test compatibility
        self.redis = redis_client
        self.agent_name = agent_name
        self.source_agent_name = agent_name  # For test compatibility
        self.config = config or CommunicationConfig()
        self.stream_manager = RedisStreamManager(redis_client)
        self.state_manager = AgentStateManager(redis_client, agent_name)
        
        # Task tracking
        self.active_tasks: Dict[str, Dict[str, Any]] = {}  # Store as dicts for test compatibility
        self.response_callbacks: Dict[str, Callable[[TaskResponse], Awaitable[None]]] = {}
        
        # Stream tracking for test compatibility
        self.last_read_ids: Dict[str, str] = {}
        
        # State
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None
    
    async def delegate_task(
        self,
        target_agent: str,
        task_data: Dict[str, Any],
        response_callback: Optional[Callable[[TaskResponse], Awaitable[None]]] = None
    ) -> str:
        """Delegate a task to the target agent.
        
        Args:
            target_agent: Name of the target agent (e.g., "bear")
            task_data: Task data dictionary
            response_callback: Optional callback for responses
            
        Returns:
            Task ID for tracking
        """
        # Generate or use task ID - preserve original ID if provided
        if isinstance(task_data, dict) and "id" in task_data:
            task_id = f"{task_data['id']}_{str(uuid4())[:8]}"  # Combine original with unique suffix
        else:
            task_id = str(uuid4())
        
        # Create task object if needed, or extract task_id from dict
        if isinstance(task_data, dict):
            # Prepare message data with required fields
            message_data = {
                **task_data,
                "id": task_id,
                "task_id": task_id,  # For test compatibility
                "target_agent": target_agent,
                "assigned_to": target_agent,  # For test compatibility
                "source_agent": self.agent_name,
                "created_at": datetime.utcnow().isoformat(),
                "status": "delegated"
            }
            
            # Store task data with additional metadata for tracking
            task_metadata = {
                **message_data,
                "last_response": None
            }
            
            self.active_tasks[task_id] = task_metadata
        else:
            # Handle DelegationTask objects for backward compatibility
            task_dict = task_data.dict()
            task_dict["id"] = task_id
            task_dict["task_id"] = task_id
            task_dict["assigned_to"] = target_agent
            task_dict["target_agent"] = target_agent
            task_dict["source_agent"] = self.agent_name
            task_dict["status"] = "delegated"
            
            message_data = task_dict
            self.active_tasks[task_id] = message_data
        
        if response_callback:
            self.response_callbacks[task_id] = response_callback
        
        # Send task to target agent's command stream
        stream_name = f"{target_agent}:commands"
        await self.stream_manager.send_message(
            stream_name,
            message_data
        )
        
        # Save active tasks state
        await self._save_active_tasks()
        
        logger.info(f"Delegated task {task_id} to {target_agent}")
        return task_id
    
    async def start_listening(self) -> None:
        """Start listening for task responses."""
        if self._running:
            return
        
        self._running = True
        
        # Load previous state
        await self._load_state()
        
        # Create consumer group for responses
        await self.stream_manager.create_consumer_group(
            self.config.response_stream,
            f"{self.agent_name}_responses"
        )
        
        # Start response listener
        self._listener_task = asyncio.create_task(self._listen_for_responses())
        
        logger.info(f"Agent {self.agent_name} started listening for responses")
    
    async def stop_listening(self) -> None:
        """Stop listening for responses."""
        self._running = False
        
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        
        # Save current state
        await self._save_state()
        
        logger.info(f"Agent {self.agent_name} stopped listening")
    
    async def wait_for_response(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> TaskResponse:
        """Wait for a specific task response.
        
        Args:
            task_id: Task ID to wait for
            timeout: Optional timeout in seconds
            
        Returns:
            Task response
            
        Raises:
            asyncio.TimeoutError: If timeout reached
            ValueError: If task not found
        """
        if task_id not in self.active_tasks:
            raise ValueError(f"Task {task_id} not found in active tasks")
        
        timeout_duration = timeout or self.config.task_timeout
        
        # Create future for response
        response_future = asyncio.Future()
        
        async def response_handler(response: TaskResponse) -> None:
            if not response_future.done():
                response_future.set_result(response)
        
        # Set temporary callback
        self.response_callbacks[task_id] = response_handler
        
        try:
            return await asyncio.wait_for(response_future, timeout=timeout_duration)
        finally:
            # Clean up callback
            self.response_callbacks.pop(task_id, None)
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a task.
        
        Args:
            task_id: Task ID to check
            
        Returns:
            Task data dictionary or None if not found
        """
        if task_id not in self.active_tasks:
            return None
        
        return self.active_tasks[task_id]
    
    async def get_task_responses(self, target_agent: str) -> List[Dict[str, Any]]:
        """Get task responses from a target agent.
        
        Args:
            target_agent: Name of the target agent
            
        Returns:
            List of response dictionaries
        """
        response_stream = f"responses:{self.agent_name}"
        
        # Use last read ID for this stream
        last_id = self.last_read_ids.get(response_stream, "0")
        
        # Read messages from response stream
        messages = await self.stream_manager.read_messages(
            {response_stream: last_id},
            count=100
        )
        
        responses = []
        new_last_id = last_id
        
        if response_stream in messages:
            for message_id, fields in messages[response_stream]:
                # Convert bytes to strings for proper processing
                decoded_fields = {}
                for key, value in fields.items():
                    key_str = key.decode() if isinstance(key, bytes) else key
                    value_str = value.decode() if isinstance(value, bytes) else value
                    decoded_fields[key_str] = value_str
                
                responses.append(decoded_fields)
                new_last_id = message_id
                
                # Update task status if this is a status update
                task_id = decoded_fields.get("task_id")
                if task_id and task_id in self.active_tasks:
                    self.active_tasks[task_id]["last_response"] = decoded_fields
                    # Update status for any status change
                    if decoded_fields.get("status"):
                        self.active_tasks[task_id]["status"] = decoded_fields["status"]
        
        # Update last read ID
        if new_last_id != last_id:
            self.last_read_ids[response_stream] = new_last_id
        
        return responses
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get all active tasks (excluding completed/failed ones).
        
        Returns:
            List of active task dictionaries with task_id added
        """
        active_statuses = {"acknowledged", "in_progress", "delegated"}
        result = []
        for task_id, task in self.active_tasks.items():
            if task.get("status") in active_statuses:
                # Add task_id to the task dict for test compatibility
                task_with_id = task.copy()
                task_with_id["task_id"] = task_id
                result.append(task_with_id)
        return result
    
    async def get_timed_out_tasks(self, timeout_seconds: int = 3600) -> List[Dict[str, Any]]:
        """Get tasks that have timed out.
        
        Args:
            timeout_seconds: Timeout threshold in seconds
            
        Returns:
            List of timed out task dictionaries with task_id included
        """
        cutoff_time = datetime.utcnow() - timedelta(seconds=timeout_seconds)
        timed_out = []
        
        for task_id, task_data in self.active_tasks.items():
            created_at = task_data.get("created_at")
            if isinstance(created_at, str):
                # Handle ISO format timestamps
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except ValueError:
                    continue
            elif not isinstance(created_at, datetime):
                continue
                
            if created_at < cutoff_time:
                # Add task_id for test compatibility
                task_with_id = task_data.copy()
                task_with_id["task_id"] = task_id
                timed_out.append(task_with_id)
        
        return timed_out
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel an active task.
        
        Args:
            task_id: Task ID to cancel
            
        Returns:
            True if task was cancelled, False if not found
        """
        if task_id not in self.active_tasks:
            return False
        
        # Create cancellation task
        cancel_task = DelegationTask(
            id=str(uuid4()),
            thread_id=str(uuid4()),
            description=f"Cancel task {task_id}",
            priority=10,
            timeline="immediate",
            assigned_to="bear",
            success_metrics=["Task cancelled successfully"],
            estimated_impact=0.1,
            estimated_effort=0.1,
            context={"cancel_task_id": task_id, "action": "cancel"},
            created_at=datetime.utcnow(),
            deadline=None
        )
        
        await self.delegate_task("bear", cancel_task.dict())
        return True
    
    async def _listen_for_responses(self) -> None:
        """Listen for task responses from Bear agent."""
        while self._running:
            try:
                messages = await self.stream_manager.read_consumer_group(
                    self.config.response_stream,
                    f"{self.agent_name}_responses",
                    self.agent_name,
                    count=10
                )
                
                for stream_name, stream_messages in messages.items():
                    for message_id, fields in stream_messages:
                        await self._handle_response_message(message_id, fields)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in response listener: {e}")
                await asyncio.sleep(self.config.retry_delay)
    
    async def _handle_response_message(self, message_id: str, fields: Dict[str, Any]) -> None:
        """Handle incoming response message.
        
        Args:
            message_id: Redis message ID
            fields: Message fields
        """
        try:
            # Parse response
            response = TaskResponse(**fields)
            
            # Find callback
            callback = self.response_callbacks.get(response.task_id)
            if callback:
                await callback(response)
            
            # If task is complete, clean up
            if response.status in ["completed", "failed"]:
                self.active_tasks.pop(response.task_id, None)
                self.response_callbacks.pop(response.task_id, None)
                await self._save_active_tasks()
            
            # Acknowledge message
            await self.stream_manager.ack_message(
                self.config.response_stream,
                f"{self.agent_name}_responses",
                message_id
            )
            
        except Exception as e:
            logger.error(f"Error handling response message {message_id}: {e}")
    
    async def _save_state(self) -> None:
        """Save delegator state."""
        await self._save_active_tasks()
        
        metadata = {
            "agent_name": self.agent_name,
            "last_active": datetime.utcnow().isoformat(),
            "active_task_count": len(self.active_tasks)
        }
        await self.state_manager.save_agent_metadata(metadata)
    
    async def _load_state(self) -> None:
        """Load delegator state."""
        # Load active tasks
        active_tasks_data = await self.state_manager.load_active_tasks()
        for task_data in active_tasks_data:
            try:
                # Store task data as dict (already in dict format from state)
                task_id = task_data.get("id") or task_data.get("task_id")
                if task_id:
                    self.active_tasks[task_id] = task_data
            except Exception as e:
                logger.error(f"Error loading task from state: {e}")
    
    async def _save_active_tasks(self) -> None:
        """Save active tasks to state."""
        # Active tasks are already stored as dicts
        tasks_data = list(self.active_tasks.values())
        await self.state_manager.save_active_tasks(tasks_data)


class AgentDelegate:
    """Handle task execution for Bear agent."""
    
    def __init__(
        self,
        redis_client,
        agent_name: str = "bear",
        config: Optional[CommunicationConfig] = None
    ):
        """Initialize the delegate.
        
        Args:
            redis_client: AsyncIO Redis client
            agent_name: Name of this agent (default: "bear")
            config: Communication configuration (optional, will use defaults)
        """
        self.redis_client = redis_client  # For test compatibility
        self.redis = redis_client
        self.agent_name = agent_name
        self.config = config or CommunicationConfig()
        self.stream_manager = RedisStreamManager(redis_client)
        self.state_manager = AgentStateManager(redis_client, agent_name)
        
        # Task handlers
        self.task_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[Any]]] = {}
        
        # Task tracking  
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        
        # State for test compatibility
        self.running = False
        self.last_read_id = "$"  # Start from latest messages
        
        # Internal state
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None
    
    def register_handler(
        self,
        task_type: str,
        handler: Callable[[Dict[str, Any]], Awaitable[Any]]
    ) -> None:
        """Register a task handler.
        
        Args:
            task_type: Type of task to handle
            handler: Async function to handle the task (receives task as dict)
        """
        self.task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")
    
    async def start_processing(self) -> None:
        """Start processing delegated tasks."""
        if self._running:
            return
        
        self._running = True
        
        # Load previous state
        await self._load_state()
        
        # Create consumer group for tasks
        await self.stream_manager.create_consumer_group(
            self.config.delegation_stream,
            f"{self.agent_name}_tasks"
        )
        
        # Start task listener
        self._listener_task = asyncio.create_task(self._listen_for_tasks())
        
        logger.info(f"Agent {self.agent_name} started processing tasks")
    
    async def stop_processing(self) -> None:
        """Stop processing tasks."""
        self._running = False
        
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        
        # Save current state
        await self._save_state()
        
        logger.info(f"Agent {self.agent_name} stopped processing")
    
    async def send_response(self, response: TaskResponse) -> None:
        """Send task response to Colonel.
        
        Args:
            response: Task response to send
        """
        await self.stream_manager.send_message(
            self.config.response_stream,
            response.dict()
        )
        
        logger.info(f"Sent response for task {response.task_id}: {response.status}")
    
    async def send_progress(self, task_id: str, thread_id: str, message: str, progress_data: Optional[Dict[str, Any]] = None) -> None:
        """Send task progress update.
        
        Args:
            task_id: Task ID
            thread_id: Thread ID
            message: Progress message
            progress_data: Optional progress data
        """
        response = TaskResponse(
            task_id=task_id,
            thread_id=thread_id,
            status="in_progress",
            message=message,
            progress=progress_data
        )
        
        await self.send_response(response)
    
    async def _listen_for_tasks(self) -> None:
        """Listen for delegated tasks."""
        while self._running:
            try:
                messages = await self.stream_manager.read_consumer_group(
                    self.config.delegation_stream,
                    f"{self.agent_name}_tasks",
                    self.agent_name,
                    count=5
                )
                
                for stream_name, stream_messages in messages.items():
                    for message_id, fields in stream_messages:
                        await self._handle_task_message(message_id, fields)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in task listener: {e}")
                await asyncio.sleep(self.config.retry_delay)
    
    async def _handle_task_message(self, message_id: str, fields: Dict[str, Any]) -> None:
        """Handle incoming task message.
        
        Args:
            message_id: Redis message ID
            fields: Message fields
        """
        try:
            # Parse task for validation
            task = DelegationTask(**fields)
            
            # Store as dict for test compatibility
            task_data = task.dict()
            self.active_tasks[task.id] = task_data
            await self._save_active_tasks()
            
            # Send initial response
            initial_response = TaskResponse(
                task_id=task.id,
                thread_id=task.thread_id,
                status="acknowledged",
                message="Task received and will be processed",
                timestamp=datetime.utcnow()
            )
            await self.send_response(initial_response)
            
            # Process task asynchronously with dict data
            asyncio.create_task(self._process_task(task_data))
            
            # Acknowledge message
            await self.stream_manager.ack_message(
                self.config.delegation_stream,
                f"{self.agent_name}_tasks",
                message_id
            )
            
        except Exception as e:
            logger.error(f"Error handling task message {message_id}: {e}")
    
    async def _process_task(self, task_data: Dict[str, Any]) -> None:
        """Process a delegated task.
        
        Args:
            task_data: Task data to process (as dict for test compatibility)
        """
        try:
            # Send processing status
            processing_response = TaskResponse(
                task_id=task_data["id"],
                thread_id=task_data["thread_id"],
                status="in_progress",
                message="Task processing started",
                timestamp=datetime.utcnow()
            )
            await self.send_response(processing_response)
            
            # Find handler based on task description or context
            handler = None
            description = task_data.get("description", "")
            context = task_data.get("context")
            
            for task_type, task_handler in self.task_handlers.items():
                if task_type in description.lower() or (context and task_type in str(context)):
                    handler = task_handler
                    break
            
            if not handler:
                raise ValueError(f"No handler found for task: {description}")
            
            # Execute handler with task data as dict
            result = await handler(task_data)
            
            # Send success response
            success_response = TaskResponse(
                task_id=task_data["id"],
                thread_id=task_data["thread_id"],
                status="completed",
                message="Task completed successfully",
                results={"result": result} if result is not None else None,
                timestamp=datetime.utcnow()
            )
            await self.send_response(success_response)
            
        except Exception as e:
            # Send error response
            error_response = TaskResponse(
                task_id=task_data["id"],
                thread_id=task_data["thread_id"],
                status="failed",
                message=f"Task failed: {str(e)}",
                error={
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                timestamp=datetime.utcnow()
            )
            await self.send_response(error_response)
            
            logger.error(f"Task {task_data['id']} failed: {e}")
        
        finally:
            # Remove from active tasks
            self.active_tasks.pop(task_data["id"], None)
            await self._save_active_tasks()
    
    async def _save_state(self) -> None:
        """Save delegate state."""
        await self._save_active_tasks()
        
        metadata = {
            "agent_name": self.agent_name,
            "last_active": datetime.utcnow().isoformat(),
            "active_task_count": len(self.active_tasks),
            "registered_handlers": list(self.task_handlers.keys())
        }
        await self.state_manager.save_agent_metadata(metadata)
    
    async def _load_state(self) -> None:
        """Load delegate state."""
        # Load active tasks
        active_tasks_data = await self.state_manager.load_active_tasks()
        for task_data in active_tasks_data:
            try:
                # Store as dict for test compatibility
                if 'id' in task_data:
                    self.active_tasks[task_data['id']] = task_data
            except Exception as e:
                logger.error(f"Error loading task from state: {e}")
    
    async def _save_active_tasks(self) -> None:
        """Save active tasks to state."""
        tasks_data = list(self.active_tasks.values())
        await self.state_manager.save_active_tasks(tasks_data)
    
    async def listen_for_tasks(self, callback=None):
        """Listen for incoming tasks - test compatibility method."""
        if callback:
            # For test compatibility, use callback to process tasks directly
            while getattr(self, 'running', True):
                try:
                    # Use xread instead of consumer group for test compatibility
                    stream_name = f"{self.agent_name}:commands"
                    result = await self.redis_client.xread(
                        {stream_name: self.last_read_id},
                        count=10,
                        block=100  # 100ms timeout
                    )
                    
                    if not result:
                        # No messages, continue but check if we should stop
                        if not getattr(self, 'running', True):
                            break
                        # Add a small delay to prevent busy waiting and allow cancellation
                        await asyncio.sleep(0.01)
                        continue
                    
                    for stream, messages in result:
                        for message_id, fields in messages:
                            # Update last read position
                            self.last_read_id = message_id.decode() if isinstance(message_id, bytes) else message_id
                            
                            # Convert bytes to strings and prepare task data
                            task_data = {}
                            for key, value in fields.items():
                                key_str = key.decode() if isinstance(key, bytes) else key
                                value_str = value.decode() if isinstance(value, bytes) else value
                                
                                # Try to deserialize JSON for complex fields
                                try:
                                    # Check if this looks like JSON data
                                    if (value_str.startswith('{') and value_str.endswith('}')) or \
                                       (value_str.startswith('[') and value_str.endswith(']')):
                                        task_data[key_str] = json.loads(value_str)
                                    else:
                                        task_data[key_str] = value_str
                                except (json.JSONDecodeError, ValueError):
                                    # If JSON parsing fails, keep as string
                                    task_data[key_str] = value_str
                            
                            # Ensure task_id field exists for callback
                            if 'id' in task_data:
                                task_data['task_id'] = task_data['id']
                            elif 'task_id' not in task_data:
                                task_data['task_id'] = task_data.get('task_id', 'unknown')
                            
                            try:
                                # Call the provided callback
                                await callback(task_data)
                            except Exception as e:
                                logger.error(f"Callback error: {e}")
                                # Continue processing other messages
                            
                            # Check if we should stop after each message
                            if not getattr(self, 'running', False):
                                return
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in listen_for_tasks: {e}")
                    # Add delay before retry to prevent tight error loops
                    await asyncio.sleep(0.1)
                    continue
        else:
            # Normal processing mode
            await self.start_processing()
    
    async def send_task_response(self, source_agent: str, response_data: Dict[str, Any]) -> None:
        """Send task response to a specific source agent.
        
        Args:
            source_agent: Name of the agent to send response to
            response_data: Response data dictionary
        """
        # Send to agent-specific response stream
        response_stream = f"responses:{source_agent}"
        await self.stream_manager.send_message(response_stream, response_data)
        logger.info(f"Sent response to {source_agent}: {response_data.get('status', 'unknown')}")
    
    async def acknowledge_task(self, task_id: str, thread_id: str, source_agent: str, message: str = "Task acknowledged") -> None:
        """Acknowledge task receipt.
        
        Args:
            task_id: Task ID
            thread_id: Thread ID
            source_agent: Agent to send acknowledgment to
            message: Acknowledgment message
        """
        response_data = {
            "task_id": task_id,
            "thread_id": thread_id,
            "status": "acknowledged",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        await self.send_task_response(source_agent, response_data)
    
    async def update_task_progress(self, task_id: str, thread_id: str, source_agent: str, message: str, progress_data: Optional[Dict[str, Any]] = None) -> None:
        """Update task progress.
        
        Args:
            task_id: Task ID
            thread_id: Thread ID
            source_agent: Agent to send update to
            message: Progress message
            progress_data: Optional progress data
        """
        response_data = {
            "task_id": task_id,
            "thread_id": thread_id,
            "status": "in_progress",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        if progress_data:
            import json
            response_data["progress"] = json.dumps(progress_data)
        
        await self.send_task_response(source_agent, response_data)
    
    async def complete_task(self, task_id: str, thread_id: str, source_agent: str, message: str, results: Optional[Dict[str, Any]] = None) -> None:
        """Mark task as completed.
        
        Args:
            task_id: Task ID
            thread_id: Thread ID
            source_agent: Agent to send completion to
            message: Completion message
            results: Optional results data
        """
        response_data = {
            "task_id": task_id,
            "thread_id": thread_id,
            "status": "completed",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        if results:
            import json
            response_data["results"] = json.dumps(results)
        
        await self.send_task_response(source_agent, response_data)
        
        # Remove from active tasks
        self.active_tasks.pop(task_id, None)
        await self._save_active_tasks()
    
    async def fail_task(self, task_id: str, thread_id: str, source_agent: str, message: str, error_data: Optional[Dict[str, Any]] = None) -> None:
        """Mark task as failed.
        
        Args:
            task_id: Task ID
            thread_id: Thread ID
            source_agent: Agent to send failure to
            message: Failure message
            error_data: Optional error data
        """
        response_data = {
            "task_id": task_id,
            "thread_id": thread_id,
            "status": "failed",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        if error_data:
            import json
            response_data["error"] = json.dumps(error_data)
        
        await self.send_task_response(source_agent, response_data)
        
        # Remove from active tasks
        self.active_tasks.pop(task_id, None)
        await self._save_active_tasks()