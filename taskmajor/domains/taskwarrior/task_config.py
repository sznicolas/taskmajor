"""TaskConfigService — stable interface to TaskWarrior configuration."""

from __future__ import annotations

import logging
from typing import Any

from taskwarrior import TaskWarrior
from taskwarrior.dto.context_dto import ContextDTO
from taskwarrior.dto.uda_dto import UdaConfig

log = logging.getLogger(__name__)


class TaskConfigService:
    """Manage TaskWarrior configuration via py-taskwarrior ConfigStore."""

    def __init__(self, taskwarrior_client: TaskWarrior) -> None:
        self._tw = taskwarrior_client
        self._config = taskwarrior_client.config_store.config

    # ------------------------------------------------------------------
    # Timezone
    # ------------------------------------------------------------------

    def get_timezone(self) -> str:
        """Get the configured timezone (or system default if not set)."""
        tz = self._config.get("rc.timezone")
        if tz:
            return tz
        # System default
        import datetime

        return str(datetime.datetime.now(datetime.UTC).astimezone().tzinfo)

    def set_timezone(self, timezone: str) -> None:
        """Set timezone via `task config timezone <value>`.

        Args:
            timezone: IANA timezone name (e.g. 'Europe/Paris', 'UTC').

        Raises:
            ValueError: If timezone is not a valid IANA name.
        """
        import zoneinfo

        try:
            zoneinfo.ZoneInfo(timezone)
        except (zoneinfo.ZoneInfoNotFoundError, KeyError) as err:
            raise ValueError(
                f"Unknown timezone {timezone!r}. Must be a valid IANA timezone (e.g. 'Europe/Paris', 'UTC')."
            ) from err
        result = self._tw.adapter.run_task_command(["config", "timezone", timezone])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to set timezone: {result.stderr}")
        log.info("Timezone set to %r", timezone)

    # ------------------------------------------------------------------
    # UDAs
    # ------------------------------------------------------------------

    def add_uda(self, uda_config: UdaConfig) -> None:
        """Add or update a UDA in the configuration using the UdaConfig DTO.

        The DTO encapsulates all UDA properties and validation.

        Args:
            uda_config: A UdaConfig DTO instance with name, uda_type, label, and optional values/default.

        Raises:
            ValueError: If the UDA configuration is invalid.
        """
        # Warn if a numeric UDA is defined with a 'values' list — such values
        # are not applicable to numeric UDAs and likely indicate a user mistake.
        try:
            uda_type = getattr(uda_config, "uda_type", None)
            values = getattr(uda_config, "values", None)
            # Normalize type name if possible
            type_name = ""
            if uda_type is not None:
                if isinstance(uda_type, str):
                    type_name = uda_type.lower()
                else:
                    # Some DTOs may use enum-like objects
                    type_name = str(uda_type).lower()
            if type_name in ("numeric", "number", "integer", "int", "float") and values:
                log.warning(
                    "UDA %r declared numeric but provided 'values' list; 'values' are ignored for numeric types.",
                    getattr(uda_config, "name", "<unknown>"),
                )
        except Exception:
            # Non-fatal: do not prevent UDA creation for unexpected DTO shapes
            log.debug("Could not inspect UdaConfig for numeric/values consistency", exc_info=True)

        self._tw.uda_service.define_uda(uda_config)
        log.info(f"UDA '{uda_config.name}' (type={uda_config.uda_type}) configured")

    def delete_uda(self, name: str) -> None:
        """Remove a UDA from configuration by delegating to the TaskWarrior API (pytaskwarrior>=2.0.4)."""
        uda = self._tw.get_uda_config(name)
        if uda:
            self._tw.delete_uda(uda)
            log.info(f"UDA '{name}' removed")
        else:
            log.warning(f"UDA '{name}' cannot be removed")

    # ------------------------------------------------------------------
    # Contexts
    # ------------------------------------------------------------------

    def get_all_config(self) -> dict[str, Any]:
        """Return entire configuration dictionary."""
        return dict(self._config)

    def get_contexts(self) -> list[ContextDTO]:
        """Get all defined contexts with their filters."""
        return self._tw.config_store.get_contexts()

    def define_context(self, context: ContextDTO) -> None:
        """Define a TaskWarrior context using the ContextDTO DTO.

        Args:
            context: A ContextDTO instance with name, read_filter, and write_filter.

        Raises:
            ValueError: If the context configuration is invalid.
        """
        self._tw.context_service.define_context(context)
        log.info(f"Context '{context.name}' defined")

    def delete_context(self, name: str) -> None:
        """Delete a context definition by delegating to the TaskWarrior ContextService."""
        self._tw.context_service.delete_context(name)
        log.info(f"Context '{name}' deleted")

    # ------------------------------------------------------------------
    # Sync
    # ------------------------------------------------------------------

    def get_sync_config(self) -> dict[str, str]:
        """Get sync server configuration if present."""
        return self._tw.config_store.get_sync_config()

    def run_sync(self) -> tuple[bool, str]:
        """Execute task sync if configured, otherwise log and return not-configured.

        Returns:
            (True, message) if sync executed successfully.
            (False, message) if sync not configured or failed.
        """
        if not self._tw.is_sync_configured():
            msg = "Sync not configured"
            log.info(msg)
            return False, msg

        try:
            self._tw.synchronize()
            msg = "Sync successful"
            log.info(msg)
            return True, msg
        except Exception as e:
            msg = f"Sync failed: {str(e)}"
            log.exception(msg)
            return False, msg
