"""
Core logic for TaskMajor server, separated from CLI and package entrypoints.
"""

from __future__ import annotations

import argparse
import logging
from copy import deepcopy
from typing import Literal, cast

from fastmcp import FastMCP
from fastmcp.resources import FunctionResource
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from pydantic import AnyUrl
from taskwarrior import TaskWarrior
from taskwarrior.dto.uda_dto import UdaConfig, UdaType

from taskmajor.domains.observability import (
    AgentErrorLog,
    configure_telemetry,
    patch_mcp_instrumentation,
)
from taskmajor.domains.profiles import ProfileConflictError, ProfileManager
from taskmajor.domains.tasks import TaskService
from taskmajor.domains.taskwarrior import TaskMajorConfig, config
from taskmajor.domains.taskwarrior.config import SyncConfig
from taskmajor.domains.taskwarrior.init import init_taskwarrior
from taskmajor.mcp import register_all
from taskmajor.utils.taskwarrior_proxy import TaskWarriorProxy

log = logging.getLogger(__name__)


def resolve_sync_config(sync_cfg: SyncConfig, args: argparse.Namespace) -> SyncConfig:
    """Apply CLI overrides on top of the already-parsed SyncConfig.

    CLI flags take precedence over config.yaml values. Only flags that were
    explicitly provided (non-None sentinel) are applied.

    Evaluation order:
    1. Backend flags (--sync-local-dir, --sync-remote-origin) can auto-enable sync.
    2. --sync-enabled / --no-sync is applied last and always wins.

    Args:
        sync_cfg: Parsed SyncConfig from TaskMajorConfig (loaded from config.yaml).
        args:     Parsed argparse.Namespace from start_mcp().

    Returns:
        A new SyncConfig instance with CLI overrides applied.
    """
    data = deepcopy(sync_cfg.model_dump())

    # --sync-mode
    if getattr(args, "sync_mode", None) is not None:
        data["mode"] = args.sync_mode

    # --sync-interval
    if getattr(args, "sync_interval", None) is not None:
        data["interval_seconds"] = args.sync_interval

    # --sync-local-dir: set path + auto-enable local + top-level sync
    if getattr(args, "sync_local_dir", None) is not None:
        local = data.setdefault("local", {})
        local["enabled"] = True
        local["server_dir"] = args.sync_local_dir
        data["enabled"] = True

    # --sync-remote-origin: set origin + auto-enable remote + top-level sync
    if getattr(args, "sync_remote_origin", None) is not None:
        remote = data.setdefault("remote", {})
        remote["enabled"] = True
        remote["origin"] = args.sync_remote_origin
        data["enabled"] = True

    # --sync-remote-client-id
    if getattr(args, "sync_remote_client_id", None) is not None:
        remote = data.setdefault("remote", {})
        remote["client_id"] = args.sync_remote_client_id

    # --sync-enabled / --no-sync applied last so it always wins over auto-enable
    if getattr(args, "sync_enabled", None) is not None:
        data["enabled"] = args.sync_enabled

    return SyncConfig.model_validate(data)


def parse_profile_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    # Single profile only (config.profile or CLI override)
    parser.add_argument("--profile", dest="profile", default=None)
    parser.add_argument("--no-profiles", action="store_true", default=False)
    parser.add_argument(
        "--transport",
        dest="transport",
        default=None,
        help="MCP transport (stdio, streamable-http, sse)",
    )
    return parser.parse_known_args()[0]


def _apply_profile(
    mcp: FastMCP, task_service: TaskService, profile_manager: ProfileManager
) -> None:
    """Apply all profile contributions from the loaded chain: UDAs, contexts, prompts, and resources.

    Processes the profile chain (parents first, child last) to apply:
    - UDAs (from all profiles)
    - Contexts (from all profiles)
    - Prompts (registered dynamically)
    - Resources (registered dynamically)
    """
    manifests = profile_manager.get_loaded_profiles()
    if not manifests:
        return

    # Apply UDAs and contexts from all profiles in the chain (parents first, child last)
    for manifest in manifests:
        log.info("Applying profile: %s (v%s)", manifest.name, manifest.version)

        # UDAs
        for uda in manifest.udas:
            try:
                task_service.task_config.add_uda(
                    UdaConfig(
                        name=uda.name,
                        uda_type=cast(UdaType, uda.type),
                        label=uda.label,
                        values=uda.values or None,
                        default=uda.default or None,
                    )
                )
                log.debug("Registered UDA '%s' from profile '%s'", uda.name, manifest.name)
            except Exception as exc:
                log.warning(
                    "Failed to register UDA '%s' from profile '%s': %s",
                    uda.name,
                    manifest.name,
                    exc,
                )

        # Contexts
        for ctx in manifest.contexts:
            try:
                # Import ContextDTO if not already imported
                from taskwarrior.dto.context_dto import ContextDTO

                task_service.task_config.define_context(
                    ContextDTO(
                        name=ctx.name,
                        read_filter=ctx.read_filter,
                        write_filter=ctx.write_filter,
                    )
                )
                log.debug("Defined context '%s' from profile '%s'", ctx.name, manifest.name)
            except Exception as exc:
                log.warning(
                    "Failed to define context '%s' from profile '%s': %s",
                    ctx.name,
                    manifest.name,
                    exc,
                )

    # Prompts (from all profiles, merged by PromptLoader)
    prompt_loader = profile_manager.get_prompt_loader()
    for prompt_name in prompt_loader.list_prompts():
        if not prompt_name or not prompt_name.strip():
            log.warning("Skipping registration of prompt with empty name")
            continue
        definition = prompt_loader.get_prompt_definition(prompt_name)
        if definition is None:
            log.warning("Skipping empty prompt %s", prompt_name)
            continue
        log.info(
            "Registering prompt '%s' from profile '%s'", prompt_name, definition.source_profile
        )

        def _make_prompt_callable(name: str):
            def _dynamic_prompt() -> str:
                prompt = prompt_loader.get_prompt(name)
                if prompt is None:
                    raise KeyError(f"Prompt not found: {name}")
                return prompt

            return _dynamic_prompt

        mcp.prompt(name=prompt_name, description=f"Prompt: {prompt_name}")(
            _make_prompt_callable(prompt_name)
        )

    # Resources (from all profiles, merged by ResourceMapper)
    resource_mapper = profile_manager.get_resource_mapper()
    for uri in resource_mapper.list_resources():
        resource_def = resource_mapper.get_resource(uri)
        if resource_def is None:
            continue
        handler = resource_mapper.create_handler(uri)
        log.info("Registering resource '%s' from profile", uri)
        mcp.add_resource(
            FunctionResource(
                uri=cast(AnyUrl, uri),
                name=resource_def.name,
                description=resource_def.description,
                mime_type="application/json",
                fn=handler,
            )
        )


def create_mcp(
    cfg: TaskMajorConfig | None = None,
    cli_profile: str | None = None,
) -> tuple[FastMCP, TaskService, AgentErrorLog]:
    """Factory that creates and initializes the FastMCP server and related services.

    This moves import-time side-effects into an explicit function so importing
    the package does not perform heavy initialization. If cfg is None the
    module-level `config` is used.

    Order of operations:
    1. Setup telemetry and MCP
    2. Initialize TaskWarrior client
    3. Load profile
    4. Create TaskService
    5. Apply profile components (UDAs, contexts, prompts, resources)
    """
    cfg = cfg or config

    configure_telemetry(
        service_name=cfg.otel_service_name or cfg.server_name,
        log_level=getattr(logging, cfg.log_level.upper()),
        log_format=cfg.log_format,
        otel_enabled=cfg.otel_enabled,
        traces_endpoint=cfg.otel_traces_endpoint or cfg.otel_exporter_endpoint,
        metrics_endpoint=cfg.otel_metrics_endpoint or cfg.otel_exporter_endpoint,
        logs_endpoint=cfg.otel_logs_endpoint or cfg.otel_exporter_endpoint,
        resource_attributes={"fastmcp.server.name": cfg.server_name},
    )

    # Log TaskWarrior config (taskrc and taskdata) now that logging is configured
    if cfg.taskdata:
        log.info(
            "Using TaskWarrior configuration: taskrc=%s, taskdata=%s", cfg.taskrc, cfg.taskdata
        )
    else:
        log.info("Using TaskWarrior configuration: taskrc=%s, taskdata=<isolated>", cfg.taskrc)

    # Log TaskMajor config file path
    log.info("TaskMajor config file: %s", getattr(cfg, "config_file", "<none>"))

    # Instrument HTTPX for OpenTelemetry
    HTTPXClientInstrumentor().instrument()

    mcp = FastMCP(name=cfg.server_name)
    patch_mcp_instrumentation(mcp)
    init_taskwarrior(cfg)

    _taskrc = cfg.taskrc
    _taskdata = cfg.taskdata
    taskwarrior_client = TaskWarriorProxy(
        factory=lambda: TaskWarrior(taskrc_file=_taskrc, data_location=_taskdata)
    )
    import atexit

    atexit.register(taskwarrior_client.shutdown)

    # Create SyncEngine if sync is enabled in config
    sync_engine = None
    if cfg.sync.enabled:
        from taskmajor.domains.sync.sync_engine import SyncEngine

        sync_engine = SyncEngine(taskwarrior_client, cfg.sync.model_dump())
        sync_engine.start()
        atexit.register(sync_engine.stop)
        log.info(
            "[SyncEngine] Initialized (mode=%s, interval=%ds, on_exit=%s)",
            cfg.sync.mode,
            cfg.sync.interval_seconds,
            cfg.sync.on_exit,
        )

    profile_manager = ProfileManager(cfg, cli_profile=cli_profile)
    error_log = AgentErrorLog(cfg.agent_errors_path)

    try:
        profile_manager.load_all()
    except ProfileConflictError as exc:
        log.error("Profile conflict: %s", exc)
        raise

    task_service = TaskService(taskwarrior_client=taskwarrior_client)

    # Attach task_service to ProfileManager so ResourceMapper can use it
    profile_manager.set_task_service(task_service)
    # Load resources now that task_service is available
    profile_manager.load_components()

    mcp.instructions = profile_manager.get_instructions()

    # Compute effective tool whitelist: union of all tools declared in the profile chain.
    # If no profile in the chain declares any tools, the whitelist is empty (no tools registered).
    tool_whitelist: set[str] = set()
    for manifest in profile_manager.get_loaded_profiles():
        tool_whitelist.update(manifest.tools)
    log.info("Effective tool whitelist (%d tools): %s", len(tool_whitelist), sorted(tool_whitelist))

    register_all(mcp, task_service, error_log, tool_whitelist=tool_whitelist, sync_engine=sync_engine)
    _apply_profile(mcp, task_service, profile_manager)

    return mcp, task_service, error_log


async def start_mcp(config_override: TaskMajorConfig | None = None) -> None:
    """Main function to run the TaskMajor server.

    This will create/initialize the MCP and then run it. Prefer using
    create_mcp() directly for tests to avoid starting the server.

    If TaskWarrior is not available on the PATH, print a friendly message
    and exit with a helpful link to the py-taskwarrior build documentation.
    """
    # Parse command-line arguments for configuration overrides
    parser = argparse.ArgumentParser()
    parser.add_argument("--taskrc", help="TaskWarrior config file path")
    parser.add_argument("--taskdata", help="TaskWarrior data directory path")
    parser.add_argument("--server-port", type=int, help="Server port number")
    parser.add_argument("--server-host", help="Server host address")
    parser.add_argument("--log-level", help="Log level")
    parser.add_argument("--profile", help="Profile name to use")
    parser.add_argument("--transport", help="MCP transport (stdio, streamable-http, sse)")
    parser.add_argument("--no-profiles", action="store_true", help="Disable profile loading")

    # Sync CLI flags (all optional — CLI overrides config.yaml)
    sync_group = parser.add_mutually_exclusive_group()
    sync_group.add_argument(
        "--sync-enabled",
        dest="sync_enabled",
        action="store_true",
        default=None,
        help="Enable TaskWarrior sync (overrides config.yaml)",
    )
    sync_group.add_argument(
        "--no-sync",
        dest="sync_enabled",
        action="store_false",
        help="Disable TaskWarrior sync (overrides config.yaml)",
    )
    parser.add_argument(
        "--sync-mode",
        choices=["periodic", "manual"],
        default=None,
        help="Sync mode: periodic (timer) or manual (force_sync tool only)",
    )
    parser.add_argument(
        "--sync-interval",
        type=int,
        default=None,
        metavar="SECONDS",
        help="Periodic sync interval in seconds (default: 300)",
    )
    parser.add_argument(
        "--sync-local-dir",
        default=None,
        metavar="PATH",
        help="Local sync server directory. Enables local sync and top-level sync.",
    )
    parser.add_argument(
        "--sync-remote-origin",
        default=None,
        metavar="URL",
        help="Remote sync server URL. Enables remote sync and top-level sync.",
    )
    parser.add_argument(
        "--sync-remote-client-id",
        default=None,
        metavar="UUID",
        help="Client UUID for remote sync server.",
    )
    # Note: --sync-remote-secret is intentionally omitted — passing secrets on the
    # command line exposes them in process listings (ps aux) and shell history.
    # Set encryption_secret in config.yaml instead.

    # Parse all additional arguments as config overrides, but keep command-line args separate
    cfg = config_override or config

    # Parse arguments and update config if necessary
    args, unknown_args = parser.parse_known_args()

    # Apply configuration overrides from command-line arguments
    if args.taskrc:
        cfg.taskrc = args.taskrc
    if args.taskdata:
        cfg.taskdata = args.taskdata
    if args.server_port:
        cfg.server_port = args.server_port
    if args.server_host:
        cfg.server_host = args.server_host
    if args.log_level:
        cfg.log_level = args.log_level

    # Apply sync CLI overrides (CLI > config.yaml)
    cfg.sync = resolve_sync_config(cfg.sync, args)

    # Determine profile from command line or config
    if args.profile:
        cli_profile = args.profile
    elif not args.no_profiles and cfg.profile:
        cli_profile = cfg.profile
    else:
        cli_profile = None

    # Determine transport: CLI override > config > default
    transport = cfg.server_transport
    if getattr(args, "transport", None):
        transport = args.transport

    log.info(f"Using MCP transport: {transport}")

    try:
        mcp, task_service, _ = create_mcp(cfg, cli_profile=cli_profile)
    except Exception as exc:
        # If the underlying error is a TaskConfigurationError from pytaskwarrior,
        # provide a friendly, actionable message. Otherwise re-raise.
        try:
            # Import here to avoid a hard dependency at module import time
            from taskwarrior import TaskConfigurationError  # type: ignore
        except Exception:
            raise

        if isinstance(exc, TaskConfigurationError):
            import sys

            msg = (
                "TaskMajor cannot start because the TaskWarrior 'task' command was not found.\n"
                "Please ensure TaskWarrior is installed and available in PATH, and that\n"
                "pytaskwarrior is correctly configured. See the build instructions:\n"
                "https://pytaskwarrior.readthedocs.io/en/latest/building-taskwarrior/\n\n"
                "Original error: "
            )
            print(msg, file=sys.stderr)
            print(str(exc), file=sys.stderr)
            raise SystemExit(1) from exc
        # Not a TaskConfigurationError - re-raise so the caller/test sees it
        raise
    info = task_service.taskwarrior_client.get_info()
    backend_type = info.get("backend_type", "")
    if backend_type != "taskchampion":
        # CLI adapter: verify the TaskWarrior binary is version 3.x
        version = info.get("backend_version", "")
        if not (isinstance(version, str) and version.startswith("3")):
            import sys

            msg = (
                "TaskMajor cannot start because the TaskWarrior 'task' version should be '3.*.*'.\n"
                "If your TaskWarrior version is older, please ensure TaskWarrior is installed and available in PATH, and that\n"
                "pytaskwarrior is correctly configured. See the build instructions:\n"
                "https://pytaskwarrior.readthedocs.io/en/latest/building-taskwarrior/\n\n"
            )
            print(msg, file=sys.stderr)
            raise SystemExit(1)

    # Run MCP transport. Don't pass port/host for stdio transport implementations
    # because run_stdio_async() does not accept these keyword arguments.
    cast_transport = cast(Literal['stdio', 'http', 'sse', 'streamable-http'] | None, transport)
    if transport == "stdio":
        await mcp.run_async(transport=cast_transport)
    else:
        await mcp.run_async(transport=cast_transport, port=cfg.server_port, host=cfg.server_host)


async def main():
    """Main entry point for the TaskMajor server."""
    await start_mcp()
