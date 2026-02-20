# Agent Core Utils

Shared utility library providing LLM initialization, Redis clients, location tools, browser automation, and inter-agent communication.

## Tech Stack
- Python 3.10+, Pydantic 2.0 for data validation
- LangChain (langchain-core, langchain-openai) for LLM integration
- Redis 5.0+ (sync and async clients, Streams for messaging)
- Selenium + webdriver-manager for browser automation
- geopy for geocoding (Nominatim)
- httpx for async HTTP

## Project Layout
- `agent_core_utils/` -- main package
- `agent_core_utils/services.py` -- factory functions: `initialize_llm_client()`, `initialize_browser_driver()`, `get_redis_client()`
- `agent_core_utils/location_tools.py` -- geocoding, bounding box, region containment
- `agent_core_utils/reasoning_tools.py` -- LLM text/HTML analysis, structured extraction
- `agent_core_utils/delegation.py` -- AgentDelegator / AgentDelegate for task coordination
- `agent_core_utils/protocols.py` -- Pydantic models: DelegationTask, TaskResponse, TaskError, TaskProgress
- `agent_core_utils/redis_streams.py` -- Redis Streams wrapper
- `agent_core_utils/redis_utils.py` -- sync/async Redis client factories
- `agent_core_utils/state_persistence.py` -- Redis-backed state management
- `agent_core_utils/config.py` -- CommunicationConfig Pydantic model
- `agent_core_utils/browser.py` -- WebDriver initialization
- `tests/` -- unit tests

## Conventions
- All configuration is environment-driven (env vars with sensible defaults)
- Graceful fallbacks for missing services (e.g., DummyDriver if Chrome unavailable)
- Pydantic models enforce validation at boundaries
- Async/await for Redis Streams and inter-agent communication
- Standard Python `logging` module with per-module loggers

## Testing
- Unit tests in `tests/` with class-based organization
- All external deps mocked (Redis, HTTP, LLM)
- Async tests use `pytest-asyncio`
- `llm` marker for tests that require LLM mocking
- Run: `pytest tests/ -v`

## Public Repository
This repository is **public on GitHub**. All code is visible to everyone. Before adding code here:
- It must be completely generic with no business logic or competitive advantages
- It must contain no proprietary algorithms or domain-specific logic
- It must contain no API keys, passwords, or secrets
- Default choice for new code is private shared libraries -- only put code here if it's explicitly intended to be public
- When in doubt, keep it private

## Code Quality
- Run `ruff check . --fix` after every code change -- zero violations allowed
- CI will fail if any ruff violations exist

## Important
This is a library, not a standalone service. Changes here affect all downstream consumers. Be conservative with breaking changes to public APIs.
