"""Compatibility shim for location tools API.

Exports `extract_location_with_llm` and `address_in_region` by importing from
the top-level `agent_core_utils.location_tools` module to satisfy legacy imports.
"""

from __future__ import annotations

from ..location_tools import extract_location_with_llm, address_in_region  # re-export

__all__ = ["extract_location_with_llm", "address_in_region"]
