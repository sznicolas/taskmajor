"""Shared utilities for MCP resource handlers."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)


def resource_response(fn: Callable[[], Any]) -> str:
    """Execute fn, serialize the result to JSON, and return an error JSON on failure."""
    try:
        return json.dumps(fn(), default=str)
    except Exception as e:
        log.debug("Resource handler raised an exception", exc_info=True)
        return json.dumps({"error": str(e)})
