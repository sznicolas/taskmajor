"""
Core logic for TaskMajor server, separated from CLI and package entrypoints.
"""

from __future__ import annotations

import argparse
import logging
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
from taskmajor.domains.taskwarrior.init import init_taskwarrior
from taskmajor.mcp import register_all

log = logging.getLogger(__name__)


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
    taskwarrior_client = TaskWarrior(
        taskrc_file=cfg.taskrc,
        data_location=cfg.taskdata,
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

    register_all(mcp, task_service, error_log, tool_whitelist=tool_whitelist)
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
    version = info.get("version")
    if not (isinstance(version, str) and version.startswith("3")):
        import sys

        msg = (
            "TaskMajor cannot start because the TaskWarrior 'task' version shoud be '3.*.*'.\n"
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
