# agent-core-utils

Shared utility library for agent applications, providing LLM initialization, Redis clients, location tools, browser automation, reasoning utilities, and inter-agent communication via Redis Streams.

## Installation

Install via pip (from the project root):

```sh
pip install .
```

For development/editable install:

```sh
pip install -e ".[dev]"
```

## Modules

### services.py

Factory functions for initializing shared infrastructure components.

- **`initialize_llm_client()`** - Returns a `ChatOpenAI` client configured from environment variables (`LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_TEMPERATURE`, `LLM_DISABLE_TEMPERATURE`). Automatically wires Langfuse tracing callbacks when `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set.
- **`initialize_browser_driver()`** - Returns a headless Chrome WebDriver, falling back to a `DummyDriver` (requests-based) if Chrome is unavailable.
- **`get_redis_client()`** - Returns a singleton async Redis client configured from `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_USERNAME`, `REDIS_PASSWORD`.
- **`get_redis_url()`** - Builds a Redis connection URL from environment variables, or returns `REDIS_URL` directly if set.

```python
from agent_core_utils.services import initialize_llm_client, get_redis_client

llm = initialize_llm_client()
redis = get_redis_client()
```

### redis_utils.py

Standalone Redis client factories (sync and async) for agents that need direct Redis access without the singleton pattern.

- **`get_redis_client()`** - Returns a synchronous `redis.Redis` client.
- **`get_async_redis_client()`** - Returns an async `redis.asyncio.Redis` client.

Both read from the same environment variables (`REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_USERNAME`, `REDIS_PASSWORD`).

### location_tools.py

Geocoding, bounding box calculations, and geographic region containment.

- **`address_in_region(address, region, *, geolocator=None)`** - Checks if an address falls within a geographic region using bounding boxes. Falls back to Nominatim geocoding.
- **`extract_location_with_llm(text, *, llm_client=None)`** - Extracts a location string from natural language text using an LLM.
- **`_create_geolocator()`** - Creates a Nominatim geocoder instance.
- **`_safe_geocode(geolocator, location)`** - Safely geocodes a location, returning `(lat, lon)` or `None`.
- **`_bounding_box(lat, lon, radius_miles=25)`** - Calculates a `(south, north, west, east)` bounding box.

```python
from agent_core_utils.location_tools import address_in_region, extract_location_with_llm

in_region = address_in_region("Central Park, NYC", "New York")
location = extract_location_with_llm("Find coffee shops near downtown Seattle")
```

### reasoning_tools.py

LLM-based text analysis and structured data extraction.

- **`analyze_text_with_llm(llm_client, text_to_analyze, question)`** - Sends text to an LLM with a question prompt. Strips markdown code fences from JSON responses.
- **`analyze_html_with_llm(llm_client, html_text, prompt)`** - Convenience wrapper for analyzing HTML content.
- **`extract_structured_data_with_llm(llm_client, text, prompt, model_class=None)`** - Extracts JSON data from text, optionally validating against a Pydantic model.

```python
from agent_core_utils.reasoning_tools import extract_structured_data_with_llm
from agent_core_utils.services import initialize_llm_client

llm = initialize_llm_client()
data = extract_structured_data_with_llm(llm, page_text, "Extract the venue name and address as JSON.")
```

### Agent Communication Framework

A Redis Streams-based system for inter-agent task delegation and response handling.

#### protocols.py

Pydantic models defining the communication contract:

- **`DelegationTask`** - Task structure with priority, timeline, success metrics, effort/impact estimates, and deadlines.
- **`TaskResponse`** - Response with status (`acknowledged`, `in_progress`, `completed`, `failed`), results, errors, and retry info.
- **`TaskError`** - Structured error with error code, message, and retry guidance.
- **`TaskProgress`** - Progress tracking with step counts and estimated completion.

#### config.py

- **`CommunicationConfig`** - Pydantic model for Redis connection settings, stream names, timeouts, retry parameters, and cleanup intervals.

#### redis_streams.py

- **`RedisStreamManager`** - Low-level Redis Streams operations: `send_message()`, `read_messages()`, `create_consumer_group()`, `read_consumer_group()`, `ack_message()`, `get_stream_info()`, `trim_stream()`. Handles serialization/deserialization and retry logic.

#### delegation.py

- **`AgentDelegator`** - Manages task delegation: sends tasks to target agents via Redis Streams, tracks active tasks, listens for responses, handles timeouts and cancellation.
- **`AgentDelegate`** - Receives and processes delegated tasks: registers task handlers by type, sends acknowledgments/progress/completion/failure responses, persists state across restarts.

#### state_persistence.py

- **`AgentStateManager`** - Redis-backed persistence for agent state: active tasks, stream read positions, and agent metadata. Survives agent restarts.

### browser.py

Convenience module that re-exports `initialize_browser_driver()` as `initialize_driver()`.

### llm.py

Compatibility shim so that `from agent_core_utils.llm import initialize_llm_client` continues to work. Forwards to `services.initialize_llm_client()`, with a dummy fallback if dependencies are missing.

### calendar_tools.py

Standalone module (at the repo root, not inside the package) providing date parsing and calendar utilities. Converts natural language date expressions (e.g., "next Friday", "in two weeks") to Python `date` objects using `dateparser`.

## Project Structure

```
agent_core_utils/
  __init__.py          # Package exports
  services.py          # LLM, browser, Redis factory functions
  redis_utils.py       # Sync/async Redis client factories
  location_tools.py    # Geocoding and region containment
  reasoning_tools.py   # LLM text analysis and extraction
  protocols.py         # Pydantic communication models
  config.py            # CommunicationConfig model
  redis_streams.py     # Redis Streams wrapper
  delegation.py        # AgentDelegator / AgentDelegate
  state_persistence.py # Redis-backed state management
  browser.py           # Browser driver convenience wrapper
  llm.py               # Legacy import compatibility shim
  google_places.py     # Google Places bounding box (stub)
  tools/               # Compatibility shims for legacy imports
calendar_tools.py      # Standalone date parsing utilities
tests/
  conftest.py
  test_services.py
  test_location_tools.py
  test_reasoning_tools.py
  test_delegation.py
  test_agent_delegate.py
  test_protocols.py
  test_config.py
  test_redis_streams.py
  test_redis_utils.py
  test_state_persistence.py
  test_integration.py
  test_calendar_tools.py
```

## Requirements

- Python >= 3.10
- See `pyproject.toml` for full dependency list

Key dependencies: `langchain-openai`, `langchain-core`, `pydantic >= 2.0`, `redis >= 5.0`, `selenium`, `webdriver-manager`, `geopy`, `httpx`, `beautifulsoup4`, `dateparser`, `lxml`, `google-search-results`

## Testing

249 tests covering services, location tools, reasoning tools, delegation, protocols, configuration, Redis streams, state persistence, calendar tools, and integration scenarios.

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=agent_core_utils --cov-report=html

# Run a specific test file
pytest tests/test_delegation.py -v
```

All external dependencies are mocked -- tests run without Redis, network, or LLM access. Async tests use `pytest-asyncio`.

## Development

- Run `ruff check . --fix` after every code change
- All external deps must be mocked in tests
- This is a shared library -- be conservative with breaking changes to public APIs

## License

This project is licensed under the MIT License.
