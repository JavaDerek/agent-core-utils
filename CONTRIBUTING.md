# Contributing Guide

Thanks for your interest in contributing!

## Development Setup

1. Python 3.10+
2. Create and activate a virtual environment
3. Install in editable mode with dev extras:
   ```sh
   pip install -e .[dev]
   ```

## Running Tests

- All tests:
  ```sh
  pytest -v
  ```
- Only LLM-marked tests:
  ```sh
  export RUN_LLM_TESTS=1
  pytest -m llm -v
  ```

## Pull Requests

- Create a feature branch from `main`
- Keep PRs small and focused
- Include tests for new/changed behavior
- Ensure `pytest` passes and CI is green

## Code Style

- Follow existing code patterns
- Add or update docstrings for public functions

## Security

- Never commit secrets. Use GitHub Actions secrets for CI.
- Report vulnerabilities privately per SECURITY.md
