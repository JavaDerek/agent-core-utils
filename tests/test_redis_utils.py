import os
import pytest
import redis_utils

def test_get_redis_client_returns_redis_instance(monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_DB", "0")
    monkeypatch.delenv("REDIS_USERNAME", raising=False)
    monkeypatch.delenv("REDIS_PASSWORD", raising=False)
    client = redis_utils.get_redis_client()
    assert hasattr(client, 'ping')
    assert hasattr(client, 'set')
    assert hasattr(client, 'get')

def test_get_redis_client_with_password(monkeypatch):
    monkeypatch.setenv("REDIS_PASSWORD", "testpass")
    monkeypatch.delenv("REDIS_USERNAME", raising=False)
    client = redis_utils.get_redis_client()
    assert client.connection_pool.connection_kwargs["username"] == "default"
    assert client.connection_pool.connection_kwargs["password"] == "testpass"
