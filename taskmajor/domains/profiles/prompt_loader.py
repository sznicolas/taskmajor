from __future__ import annotations

import logging
from pathlib import Path

from taskmajor.domains.profiles.models import ProfileManifest, PromptDefinition

log = logging.getLogger(__name__)

PROMPTS_DIR = "prompts"


class PromptLoader:
    def __init__(self) -> None:
        self._prompts: dict[str, PromptDefinition] = {}

    def load_from_profile(self, profile_path: Path, manifest: ProfileManifest) -> None:
        # Pass 1: Filesystem scan (prompts/*.md)
        prompts_dir = profile_path / PROMPTS_DIR
        if prompts_dir.exists() and prompts_dir.is_dir():
            log.info(f"Scanning prompts from profile: {manifest.name}")
            for prompt_file in sorted(prompts_dir.glob("*.md")):
                name = prompt_file.stem
                if not name or not name.strip():
                    log.warning(f"Ignoring prompt file with empty name: {prompt_file}")
                    continue
                content = prompt_file.read_text(encoding="utf-8")
                log.debug(f"Prompt '{name}' loaded from profile '{manifest.name}'")
                self._prompts[name] = PromptDefinition(
                    name=name,
                    content=content,
                    source_profile=manifest.name,
                )
        else:
            log.debug(f"No {PROMPTS_DIR}/ directory in profile '{manifest.name}'; skipping filesystem scan.")

        # Pass 2: Manifest-declared prompts (override filesystem scan for same name)
        for decl in manifest.prompts:
            file_path = profile_path / decl.file
            if not file_path.exists():
                log.warning(
                    "Manifest-declared prompt '%s' file not found: %s",
                    decl.name,
                    file_path,
                )
                continue
            content = file_path.read_text(encoding="utf-8")
            if decl.name in self._prompts:
                log.debug(
                    "Manifest declaration overrides filesystem scan for prompt '%s' in profile '%s'",
                    decl.name,
                    manifest.name,
                )
            self._prompts[decl.name] = PromptDefinition(
                name=decl.name,
                content=content,
                source_profile=manifest.name,
            )

    def get_prompt(self, name: str) -> str | None:
        pd = self._prompts.get(name)
        return pd.content if pd else None

    def get_prompt_definition(self, name: str) -> PromptDefinition | None:
        return self._prompts.get(name)

    def list_prompts(self, audience: str | None = None) -> list[str]:
        return list(self._prompts.keys())

    def get_all_definitions(self) -> dict[str, PromptDefinition]:
        return dict(self._prompts)
