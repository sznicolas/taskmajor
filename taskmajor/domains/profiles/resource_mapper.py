from __future__ import annotations

import inspect
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar, cast

import yaml

from taskmajor.domains.profiles.models import ProfileManifest, ResourceDefinition


def deep_merge_dict(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge two dicts: dicts are merged recursively, lists and scalars are replaced by child."""
    if not parent:
        parent = {}
    if not child:
        child = {}
    result: dict[str, Any] = dict(parent)
    for k, v in child.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge_dict(result[k], v)
        else:
            result[k] = v
    return result


class ResourceMapper:
    ALLOWED_BACKENDS: ClassVar[frozenset[str]] = frozenset({
        "query_tasks",
        "get_tasks_by_scope",
        "get_stats",
        "next_task",
        "get_metadata",
        "add_task",
        "update_task",
        "get_projects",
        "get_tags",
        "get_udas",
    })

    def __init__(self, task_service: Any) -> None:
        self._resources: dict[str, ResourceDefinition] = {}
        self._task_service = task_service

    def load_from_profile(self, profile_path: Path, manifest: ProfileManifest) -> None:
        resources = list(manifest.resources)

        # Detect duplicate URIs declared directly in the manifest; this is an error
        seen: set[str] = set()
        duplicates: set[str] = set()
        for entry in resources:
            uri_val = entry.get("uri")
            # Ensure uri_val is a string before using it as a set key
            if not isinstance(uri_val, str):
                raise ValueError(f"Resource entry in manifest '{manifest.name}' missing or invalid 'uri': {entry!r}")
            if uri_val in seen:
                duplicates.add(uri_val)
            else:
                seen.add(uri_val)
        if duplicates:
            raise ValueError(
                f"Duplicate resource URI(s) in manifest '{manifest.name}': {sorted(duplicates)}"
            )

        yaml_path = profile_path / "resources.yaml"
        if yaml_path.exists():
            with yaml_path.open("r", encoding="utf-8") as f:
                yaml_resources = yaml.safe_load(f)
            if not isinstance(yaml_resources, list):
                raise ValueError("resources.yaml must contain a list of resources")
            merged: dict[str, dict] = {}
            for entry in resources:
                merged[entry["uri"]] = entry
            for entry in yaml_resources:
                merged[entry["uri"]] = entry
            resources = list(merged.values())

        for entry in resources:
            uri = entry["uri"]
            backend = entry.get("backend")
            if not backend or "function" not in backend:
                raise ValueError(f"Resource '{uri}' missing required 'backend.function' field")
            child_backend_function = backend["function"]
            if child_backend_function not in self.ALLOWED_BACKENDS:
                raise ValueError(f"Backend function '{child_backend_function}' not allowed")
            child_backend_params = backend.get("params", {}) or {}
            if not isinstance(child_backend_params, dict):
                raise ValueError(
                    f"Resource '{uri}' backend.params must be a mapping; got {type(child_backend_params).__name__}"
                )

            # Determine final backend params/function and name/description, optionally merging with parent
            if uri in self._resources:
                parent_res = self._resources[uri]
                merge_flag = bool(entry.get("merge", False))
                if merge_flag:
                    final_backend_params = deep_merge_dict(parent_res.backend_params or {}, child_backend_params)
                    logging.getLogger(__name__).info(
                        "Resource URI '%s' merged with parent by profile '%s'", uri, manifest.name
                    )
                    final_backend_function = child_backend_function
                    resource_name = entry.get("name", parent_res.name)
                    resource_description = entry.get("description", parent_res.description)
                else:
                    logging.getLogger(__name__).info(
                        "Resource URI '%s' overridden by profile '%s'", uri, manifest.name
                    )
                    final_backend_params = child_backend_params
                    final_backend_function = child_backend_function
                    resource_name = entry["name"]
                    resource_description = entry["description"]
            else:
                final_backend_params = child_backend_params
                final_backend_function = child_backend_function
                resource_name = entry["name"]
                resource_description = entry["description"]

            # Validate final backend params against the callable signature
            backend_callable = getattr(self._task_service, final_backend_function, None)
            # Only attempt to inspect signature for callables
            if not callable(backend_callable):
                sig = None
            else:
                try:
                    sig = inspect.signature(backend_callable)
                except (ValueError, TypeError) as exc:
                    logging.getLogger(__name__).debug(
                        "Could not inspect signature for backend %s: %s", final_backend_function, exc
                    )
                    sig = None

            if sig is not None:
                params_sig = sig.parameters
                accepts_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params_sig.values())
                accepts_varargs = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params_sig.values())

                # If function uses **kwargs or *args, skip validation (accept anything)
                if not accepts_kwargs and not accepts_varargs:
                    accepted = [
                        param_name
                        for param_name, p in params_sig.items()
                        if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
                    ]
                    # remove 'self' if present
                    accepted = [n for n in accepted if n != "self"]
                    invalid = [k for k in (final_backend_params or {}).keys() if k not in accepted]
                    if invalid:
                        raise ValueError(
                            f"Backend function '{final_backend_function}' does not accept parameter(s) {invalid!r}. "
                            f"Accepted: {accepted!r}. Profile: {manifest.name!r}, URI: {uri!r}, Provided: {list(final_backend_params.keys())!r}"
                        )

            self._resources[uri] = ResourceDefinition(
                uri=uri,
                name=resource_name,
                description=resource_description,
                backend_function=final_backend_function,
                backend_params=final_backend_params,
                merge=bool(entry.get("merge", False)),
            )

    def list_resources(self) -> list[str]:
        return list(self._resources.keys())

    def get_resource(self, uri: str) -> ResourceDefinition | None:
        return self._resources.get(uri)

    def create_handler(self, uri: str) -> Callable[[], str]:
        resource = self.get_resource(uri)
        if resource is None:
            raise KeyError(f"Resource URI not found: {uri}")

        # mypy can't determine resource is not None; create a typed local alias
        res: ResourceDefinition = cast(ResourceDefinition, resource)

        def _handler(resource: ResourceDefinition = res) -> str:
            try:
                payload = self._invoke_backend(resource)
            except Exception as exc:  # backend errors are surfaced as JSON payloads
                return json.dumps({"error": str(exc)})
            return json.dumps(payload, default=str)

        return _handler

    def get_all_definitions(self) -> dict[str, ResourceDefinition]:
        return dict(self._resources)

    def _invoke_backend(self, resource: ResourceDefinition) -> Any:
        backend = getattr(self._task_service, resource.backend_function)
        return backend(**resource.backend_params)
