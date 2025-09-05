import os
import redis
import redis.asyncio as async_redis

def get_redis_client():
    """
    Create and return a Redis client using environment variables for configuration.
    Shared by all agents to ensure consistent connection logic.
    Env vars used:
      REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_USERNAME, REDIS_PASSWORD
    """
    host = os.environ.get("REDIS_HOST", "localhost")
    port = int(os.environ.get("REDIS_PORT", "6379"))
    db = int(os.environ.get("REDIS_DB", "0"))
    username = os.environ.get("REDIS_USERNAME")
    password = os.environ.get("REDIS_PASSWORD")
    if not username and password:
        # Default to username 'default' if only password is provided (Redis ACL)
        username = "default"
    return redis.Redis(
        host=host,
        port=port,
        db=db,
        username=username,
        password=password,
        socket_connect_timeout=1.0,
        socket_timeout=1.0,
    )

def get_async_redis_client():
    """
    Create and return an async Redis client using environment variables for configuration.
    Shared by all agents to ensure consistent connection logic.
    Env vars used:
      REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_USERNAME, REDIS_PASSWORD
    """
    host = os.environ.get("REDIS_HOST", "localhost")
    port = int(os.environ.get("REDIS_PORT", "6379"))
    db = int(os.environ.get("REDIS_DB", "0"))
    username = os.environ.get("REDIS_USERNAME")
    password = os.environ.get("REDIS_PASSWORD")
    if not username and password:
        # Default to username 'default' if only password is provided (Redis ACL)
        username = "default"
    return async_redis.Redis(
        host=host,
        port=port,
        db=db,
        username=username,
        password=password,
        socket_connect_timeout=1.0,
        socket_timeout=1.0,
    )
