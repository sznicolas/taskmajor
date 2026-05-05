"""
TaskMajor Server - A FastMCP server for task management using pytaskwarrior
"""

from __future__ import annotations

import asyncio

from .core import main

if __name__ == "__main__":
    asyncio.run(main())
