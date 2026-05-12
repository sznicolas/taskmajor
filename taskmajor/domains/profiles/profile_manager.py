from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, ClassVar

from taskmajor.domains.profiles.instructions_loader import InstructionsLoader
from taskmajor.domains.profiles.models import ProfileManifest, UdaDefinition
from taskmajor.domains.profiles.prompt_loader import PromptLoader
from taskmajor.domains.profiles.resource_mapper import ResourceMapper
from taskmajor.domains.taskwarrior.config import TaskMajorConfig

log = logging.getLogger(__name__)


class ProfileConflictError(Exception):
    """Raised when profile composition conflicts are detected (cycle, sibling conflict, etc.)."""


class ProfileManager:
    """Load and manage a profile and its extends chain.

    Supports:
    - Profile composition via extends (parent → child chain)
    - Profile sets (shared component bundles)
    - Conflict detection (sibling resource URIs, cycles)
    - Accumulating instructions from the chain
    """

    ALLOWED_BACKENDS: ClassVar[frozenset[str]] = ResourceMapper.ALLOWED_BACKENDS

    def __init__(self, config: TaskMajorConfig, cli_profile: str | None = None):
        """Initialize ProfileManager.

        Args:
            config: TaskMajorConfig with default profile name
            cli_profile: Optional CLI override (name or absolute path)
        """
        self._config = config
        self._cli_profile = None if cli_profile in (None, []) else str(cli_profile)
        self._prompt_loader = PromptLoader()
        self._instructions_loader = InstructionsLoader()
        self._resource_mapper: ResourceMapper | None = None
        self._loaded_manifests: list[ProfileManifest] = []
        self._registered_prompt_names: dict[str, str] = {}
        self._registered_resource_uris: dict[str, str] = {}
        self._task_service: Any | None = None

    def set_task_service(self, task_service: Any) -> None:
        """Attach the TaskService for resource mapper initialization."""
        self._task_service = task_service
        self._resource_mapper = ResourceMapper(task_service)

    def load_all(self) -> list[ProfileManifest]:
        """Load a profile and its entire extends chain in two phases.

        Phase 1 (no task_service required):
        - Build and validate the extends chain
        - Load instructions and prompts

        Phase 2 (task_service required):
        - Load resources (which require TaskService for the ResourceMapper)

        Returns:
            List of ProfileManifest objects in load order (parents first, child last)

        Raises:
            RuntimeError: if task_service not set before phase 2
            FileNotFoundError: if profile not found
            ProfileConflictError: if cycle or sibling conflict detected
        """
        # Phase 1: Load chain and manifests (no task_service required)
        chain = self._load_chain()
        self._loaded_manifests = chain

        # Phase 2: Load components that require task_service
        if self._task_service is not None and self._resource_mapper is not None:
            self.load_components()

        return list(chain)

    def _load_chain(self) -> list[ProfileManifest]:
        """Phase 1: Build, validate, and load the profile chain.

        Returns:
            List of ProfileManifest objects

        Raises:
            FileNotFoundError: if profile not found
            ProfileConflictError: if cycle or sibling conflict detected
        """
        # Reset loaders (but not resource_mapper - it's not used yet)
        self._prompt_loader = PromptLoader()
        self._instructions_loader = InstructionsLoader()
        self._registered_prompt_names = {}
        self._registered_resource_uris = {}

        # Determine which profile to load
        profile_name_or_path = self._cli_profile or self._config.profile

        # Build the extends chain
        try:
            chain = self._build_chain(profile_name_or_path, visited=set())
        except ProfileConflictError:
            # Re-raise ProfileConflictError without wrapping
            raise
        except Exception as e:
            log.error(
                f"[PROFILE CHAIN ERROR] Failed to build chain for '{profile_name_or_path}': {type(e).__name__}: {e}"
            )
            raise RuntimeError(f"[PROFILE CHAIN ERROR] {type(e).__name__}: {e}") from e

        # Check for conflicts in the chain
        try:
            self._check_conflicts(chain)
        except ProfileConflictError as e:
            log.error(f"[PROFILE CONFLICT] {e}")
            raise

        # Load prompts and instructions for each manifest in the chain
        for manifest in chain:
            # Load prompts and instructions (these don't need task_service)
            try:
                self._load_prompts_and_instructions(manifest)
            except Exception as e:
                log.error(
                    f"[PROFILE LOAD ERROR] Profile '{manifest.name}': {type(e).__name__}: {e}"
                )
                raise RuntimeError(f"[PROFILE LOAD ERROR] {type(e).__name__}: {e}") from e

        # Validate UDAs across the chain (parents first)
        try:
            self._validate_udas(chain)
        except ProfileConflictError as e:
            log.error(f"[UDA VALIDATION] {e}")
            raise

        return chain

    def load_components(self) -> None:
        """Phase 2: Load resources (requires task_service and resource_mapper).

        Called after set_task_service() has been invoked.

        Raises:
            RuntimeError: if task_service not set
        """
        if self._resource_mapper is None:
            raise RuntimeError("Resource mapper must be initialized before loading components")

        for manifest in self._loaded_manifests:
            try:
                self._load_resources(manifest)
            except Exception as e:
                log.error(
                    f"[RESOURCE LOAD ERROR] Profile '{manifest.name}': {type(e).__name__}: {e}"
                )
                raise RuntimeError(f"[RESOURCE LOAD ERROR] {type(e).__name__}: {e}") from e

    def _load_prompts_and_instructions(self, manifest: ProfileManifest) -> None:
        """Load prompts and instructions from a profile (no task_service required)."""
        profile_path = manifest.path
        if profile_path is None:
            raise RuntimeError(f"Manifest '{manifest.name}' is missing its profile path")

        # Load prompts
        try:
            self._prompt_loader.load_from_profile(profile_path, manifest)
        except Exception as e:
            raise RuntimeError(f"Failed to load prompts for '{manifest.name}': {e}") from e

        # Load instructions
        self._instructions_loader.load_from_profile(profile_path, manifest)

        # Update registries
        for name in self._prompt_loader.get_all_definitions().keys():
            if name not in self._registered_prompt_names:
                defn = self._prompt_loader.get_prompt_definition(name)
                if defn:
                    self._registered_prompt_names[name] = defn.source_profile

    def _load_resources(self, manifest: ProfileManifest) -> None:
        """Load resources from a profile (requires task_service)."""
        profile_path = manifest.path
        if profile_path is None:
            raise RuntimeError(f"Manifest '{manifest.name}' is missing its profile path")

        if self._resource_mapper is None:
            raise RuntimeError("Task service must be set before loading resources")

        try:
            self._resource_mapper.load_from_profile(profile_path, manifest)
        except Exception as e:
            raise RuntimeError(f"Failed to load resources for '{manifest.name}': {e}") from e

        for uri in self._resource_mapper.get_all_definitions().keys():
            if uri not in self._registered_resource_uris:
                self._registered_resource_uris[uri] = manifest.name

    def _resolve_profile_path(self, profile: str) -> Path:
        """Resolve profile directory using 3-tier search.

        Search order:
        1. Absolute path (if provided and exists)
        2. User config: ~/.config/taskmajor/profiles/<name>/
        3. Built-in: taskmajor/profiles/<name>/

        Args:
            profile: Profile name or absolute path

        Returns:
            Resolved Path to profile directory

        Raises:
            FileNotFoundError: if profile not found in any search path
        """
        # 1. Absolute path
        candidate = Path(profile).expanduser()
        if candidate.is_absolute() and candidate.exists() and candidate.is_dir():
            log.debug("Resolved profile '%s' to absolute path: %s", profile, candidate)
            return candidate

        # 2. User config: ~/.config/taskmajor/profiles/<name>/
        user_dir = Path.home() / ".config" / "taskmajor" / "profiles" / profile
        if user_dir.exists() and user_dir.is_dir():
            log.debug("Resolved profile '%s' to user config: %s", profile, user_dir)
            return user_dir

        # 3. Built-in: taskmajor/profiles/<name>/
        pkg_dir = Path(__file__).parent.parent.parent / "profiles" / profile
        if pkg_dir.exists() and pkg_dir.is_dir():
            log.debug("Resolved profile '%s' to built-in: %s", profile, pkg_dir)
            return pkg_dir

        # Not found
        raise FileNotFoundError(
            f"Profile '{profile}' not found. Searched: "
            f"(absolute) {candidate}, "
            f"(user) {user_dir}, "
            f"(built-in) {pkg_dir}"
        )

    def _build_chain(self, name_or_path: str, visited: set[str]) -> list[ProfileManifest]:
        """Build the extends chain recursively (depth-first, parents first).

        Args:
            name_or_path: Profile name or path to load
            visited: Set of canonical paths already visited (for cycle detection)

        Returns:
            List of ProfileManifest in load order: [grandparent, ..., parent, child]

        Raises:
            FileNotFoundError: if profile not found
            ProfileConflictError: if cycle detected
        """
        # Resolve the profile path
        path = self._resolve_profile_path(name_or_path)
        canonical = str(path.resolve())

        # Cycle detection
        if canonical in visited:
            raise ProfileConflictError(
                f"Cycle detected in extends chain at '{name_or_path}' ({canonical})"
            )
        visited.add(canonical)

        # Load this profile's manifest
        try:
            manifest = ProfileManifest.from_yaml(path / "manifest.yaml")
            manifest.path = path
            log.debug("Loaded manifest for profile '%s' from %s", manifest.name, path)
        except Exception as e:
            raise FileNotFoundError(
                f"Failed to load manifest for '{name_or_path}' at {path / 'manifest.yaml'}: {e}"
            ) from e

        # Build parent chains first
        chain: list[ProfileManifest] = []
        for parent_name in manifest.extends:
            parent_chain = self._build_chain(parent_name, visited)
            chain.extend(parent_chain)

        # Append this profile last
        chain.append(manifest)
        return chain

    def _check_conflicts(self, chain: list[ProfileManifest]) -> None:
        """Check for sibling conflicts in the chain.

        Allowed:
        - Child overrides parent on same resource URI or prompt name → warning logged

        Not allowed:
        - Two siblings (same depth) declare same resource URI → ProfileConflictError
        - Two siblings declare same prompt name → ProfileConflictError

        Args:
            chain: List of ProfileManifest in order (parents first, child last)

        Raises:
            ProfileConflictError: if conflict detected
        """
        # Track (chain_depth, profile_name) for each resource URI and prompt name
        resource_owners: dict[str, tuple[int, str]] = {}  # uri -> (depth, name)
        prompt_owners: dict[str, tuple[int, str]] = {}  # name -> (depth, name)

        for depth, manifest in enumerate(chain):
            # Check resources
            for resource in manifest.resources:
                uri = resource.get("uri", "")
                if not uri:
                    continue
                if uri in resource_owners:
                    prev_depth, prev_name = resource_owners[uri]
                    if prev_depth == depth:
                        # Same depth → sibling conflict
                        raise ProfileConflictError(
                            f"Resource URI '{uri}' declared by sibling profiles '{prev_name}' and '{manifest.name}'"
                        )
                    else:
                        # Different depth → child override
                        log.warning(
                            "Profile '%s' overrides resource URI '%s' from parent '%s'",
                            manifest.name,
                            uri,
                            prev_name,
                        )
                resource_owners[uri] = (depth, manifest.name)

            # Check prompts
            for prompt in manifest.prompts:
                # PromptDeclaration is a dataclass; use attribute access
                name = getattr(prompt, "name", "")
                if not name:
                    continue
                if name in prompt_owners:
                    prev_depth, prev_name = prompt_owners[name]
                    if prev_depth == depth:
                        # Same depth → sibling conflict
                        raise ProfileConflictError(
                            f"Prompt '{name}' declared by sibling profiles '{prev_name}' and '{manifest.name}'"
                        )
                    else:
                        # Different depth → child override
                        log.warning(
                            "Profile '%s' overrides prompt '%s' from parent '%s'",
                            manifest.name,
                            name,
                            prev_name,
                        )
                prompt_owners[name] = (depth, manifest.name)

    def _validate_udas(self, chain: list[ProfileManifest]) -> None:
        """Validate UDAs across the profile chain (parents first).

        Rules:
        - If a UDA is re-declared in a descendant, its type must match the nearest ancestor's type.
        - If the ancestor declares allowed values (non-empty list), the descendant's values must be a subset.
        - If the ancestor has no allowed values, the descendant may add values.
        """
        # Map of uda_name -> (UdaDefinition, profile_name) for the most-recent declaration seen
        seen: dict[str, tuple[UdaDefinition, str]] = {}
        for manifest in chain:
            for uda in manifest.udas:
                if not uda.name:
                    continue
                if uda.name not in seen:
                    # first declaration becomes the effective definition for downstream profiles
                    seen[uda.name] = (uda, manifest.name)
                    continue
                parent_def, parent_name = seen[uda.name]
                # Type must match exactly
                if uda.type != parent_def.type:
                    raise ProfileConflictError(
                        f"UDA '{uda.name}' in profile '{manifest.name}' conflicts with parent '{parent_name}': Type mismatch ({uda.type} vs {parent_def.type})"
                    )
                parent_values = set(parent_def.values or [])
                child_values = set(uda.values or [])
                if parent_values:
                    # parent has an explicit allowed-values list: child must not introduce new values
                    added = child_values - parent_values
                    if added:
                        raise ProfileConflictError(
                            f"UDA '{uda.name}' in profile '{manifest.name}' conflicts with parent '{parent_name}': Allowed values extension not permitted (added: {sorted(added)})"
                        )
                    # Child is a subset (or equal) -> OK. Warn on strong restriction.
                    if len(child_values) < len(parent_values):
                        log.warning(
                            "UDA '%s' in profile '%s' restricts allowed values compared to parent '%s' (%d -> %d)",
                            uda.name,
                            manifest.name,
                            parent_name,
                            len(parent_values),
                            len(child_values),
                        )
                # If parent did not define allowed values, child may add values (restriction) or none (extension)
                # Record the child's declaration as the effective definition for downstream profiles
                seen[uda.name] = (uda, manifest.name)

    def _load_profile_components(self, manifest: ProfileManifest) -> None:
        """Load prompts, instructions, and resources from a single manifest.

        Args:
            manifest: ProfileManifest with path attached

        Raises:
            RuntimeError: if components fail to load
        """
        profile_path = manifest.path
        if profile_path is None:
            raise RuntimeError(f"Manifest '{manifest.name}' is missing its profile path")

        # Load prompts
        try:
            self._prompt_loader.load_from_profile(profile_path, manifest)
        except Exception as e:
            raise RuntimeError(f"Failed to load prompts for '{manifest.name}': {e}") from e

        # Load instructions
        self._instructions_loader.load_from_profile(profile_path, manifest)

        # Load resources
        if self._resource_mapper is None:
            raise RuntimeError("Task service must be set before loading profile components")

        try:
            self._resource_mapper.load_from_profile(profile_path, manifest)
        except Exception as e:
            raise RuntimeError(f"Failed to load resources for '{manifest.name}': {e}") from e

        # Update registries
        for name in self._prompt_loader.get_all_definitions().keys():
            if name not in self._registered_prompt_names:
                defn = self._prompt_loader.get_prompt_definition(name)
                if defn:
                    self._registered_prompt_names[name] = defn.source_profile

        for uri in self._resource_mapper.get_all_definitions().keys():
            if uri not in self._registered_resource_uris:
                self._registered_resource_uris[uri] = manifest.name

    def get_prompt_loader(self) -> PromptLoader:
        return self._prompt_loader

    def get_instructions_loader(self) -> InstructionsLoader:
        return self._instructions_loader

    def get_instructions(self) -> str | None:
        return self._instructions_loader.get_instructions()

    def get_resource_mapper(self) -> ResourceMapper:
        if self._resource_mapper is None:
            raise RuntimeError("Task service has not been set.")
        return self._resource_mapper

    def get_loaded_profiles(self) -> list[ProfileManifest]:
        return list(self._loaded_manifests)

    def get_diagnostics(self) -> dict:
        return {
            "loaded": [
                {"name": manifest.name, "version": manifest.version}
                for manifest in self._loaded_manifests
            ],
            "prompts": list(self._registered_prompt_names.keys()),
            "resources": list(self._registered_resource_uris.keys()),
            "instructions_sources": self._instructions_loader.source_profiles,
        }
