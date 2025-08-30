# agent-core-utils

All the tools shared between agents

## Overview

This repository contains utility modules for agents, providing essential functionality for date/time processing and location handling. The modules are designed to be reusable across different agent implementations.

## Modules

### calendar_tools.py

The `calendar_tools` module provides utilities for parsing and resolving relative date expressions into absolute dates.

#### Key Functions

- **`get_current_date()`** - Returns today's date as a `date` object
- **`parse_relative_date(expression, *, base=None)`** - Parses relative date expressions into absolute dates
- **`resolve_relative_dates(text, *, base=None)`** - Replaces relative date phrases in text with ISO date strings  
- **`_word_to_int(word)`** - Converts word numbers (e.g., "five") and digit strings to integers

#### Usage Examples

```python
from calendar_tools import get_current_date, parse_relative_date, resolve_relative_dates

# Get current date
today = get_current_date()
print(today)  # 2023-06-15

# Parse relative dates
base_date = date(2023, 6, 15)
next_month = parse_relative_date("next july", base=base_date)
print(next_month)  # 2023-07-01

ago_date = parse_relative_date("5 days ago", base=base_date) 
print(ago_date)  # 2023-06-10

future_date = parse_relative_date("in two weeks", base=base_date)
print(future_date)  # 2023-06-29

# Resolve dates in text
text = "The meeting is next july and the report was due 3 days ago."
resolved = resolve_relative_dates(text, base=base_date)
print(resolved)  # "The meeting is 2023-07-01 and the report was due 2023-06-12."
```

#### Supported Date Expressions

- **Next/Last Month**: "next july", "last december"
- **Relative Time**: "in 5 days", "2 weeks from now", "3 months ago"  
- **Word Numbers**: "five days ago", "two weeks from now"
- **Flexible Units**: supports days, weeks, months, years (singular/plural)

### location_tools.py

The `location_tools` module provides utilities for geocoding addresses, calculating bounding boxes, and determining if addresses fall within geographic regions.

#### Key Functions

- **`_create_geolocator()`** - Creates a Nominatim geocoder instance with proper user agent
- **`_safe_geocode(geolocator, location)`** - Safely geocodes a location string, returning (lat, lon) or None
- **`_bounding_box(lat, lon, radius_miles=25)`** - Calculates bounding box around coordinates
- **`address_in_region(address, region, *, geolocator=None)`** - Checks if address is within a geographic region
- **`extract_location_with_llm(text, *, llm_client=None)`** - Extracts location from text using LLM (requires OpenAI client)

#### Usage Examples

```python
from location_tools import _create_geolocator, _safe_geocode, _bounding_box, address_in_region

# Create a geocoder
geolocator = _create_geolocator()

# Geocode an address  
coords = _safe_geocode(geolocator, "New York, NY")
print(coords)  # (40.7128, -74.0060)

# Calculate bounding box around coordinates
bbox = _bounding_box(40.7128, -74.0060, radius_miles=25)
print(bbox)  # (south, north, west, east)

# Check if address is in region
is_in_region = address_in_region("Central Park, NYC", "New York", geolocator=geolocator)
print(is_in_region)  # True

# Safe geocoding handles errors gracefully
coords = _safe_geocode(geolocator, "Invalid Location XYZ")
print(coords)  # None
```

#### Features

- **Error Handling**: All functions gracefully handle network errors and invalid inputs
- **Dual Fallback**: Uses Google Places API when available, falls back to geocoding + bounding box calculation
- **Configurable Radius**: Bounding box calculations support custom radius in miles
- **LLM Integration**: Can extract locations from natural language text using OpenAI models

## Dependencies

The modules require the following packages:

```bash
pip install dateparser python-dateutil geopy langchain-openai langchain-core
```

## Testing

Comprehensive test suites are provided for both modules:

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific module tests
pytest tests/test_calendar_tools.py -v
pytest tests/test_location_tools.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

### Test Coverage

- **calendar_tools**: 51 tests covering all functions, edge cases, and parameterized scenarios
- **location_tools**: 34 tests with mocked external dependencies and boundary condition testing
- **Features tested**: Error handling, boundary conditions, parameter validation, mocking external APIs

### Test Structure

Tests follow pytest conventions with:
- Class-based organization for related test groups
- Descriptive test names following `test_<functionality>_<scenario>` pattern
- Parameterized tests for comprehensive input validation
- Proper mocking of external dependencies (geocoding APIs, LLM clients)
- Skip markers for tests requiring external services

## Development

When adding new functionality:

1. Follow existing code patterns and documentation styles
2. Add comprehensive tests with both positive and negative test cases
3. Use appropriate mocking for external dependencies
4. Update this README with new function documentation and examples
5. Ensure all tests pass before submitting changes

## License

This project is licensed under the MIT License.
