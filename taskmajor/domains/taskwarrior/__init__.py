"""TaskWarrior integration domain."""

from .config import TaskMajorConfig, config
from .task_config import TaskConfigService

__all__ = ["TaskMajorConfig", "TaskConfigService", "config"]
