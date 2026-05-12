"""
TaskMajor Server - A FastMCP server for task management using pytaskwarrior
"""

from __future__ import annotations

import asyncio
import logging

from taskmajor.domains.taskwarrior import config as _task_config

from .core import main

if __name__ == "__main__":
    # Ensure early INFO logs (like config loading) are visible before core configures logging
    logging.basicConfig(level=logging.INFO)
    logging.getLogger(__name__).info(
        "Starting TaskMajor (taskrc=%s, taskdata=%s, config=%s)",
        _task_config.taskrc,
        _task_config.taskdata or "<isolated>",
        getattr(_task_config, "config_file", "<default>"),
    )
    asyncio.run(main())
