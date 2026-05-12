from __future__ import annotations

import logging
from pathlib import Path

import yaml

from taskmajor.domains.profiles.models import ProfileManifest

log = logging.getLogger(__name__)

SEPARATOR = "\n---\n\n"


class _Fragment:
    def __init__(self, profile_name: str, content: str) -> None:
        self.profile_name = profile_name
        self.content = content


class InstructionsLoader:
    """Loads and merges instruction fragments from a profile chain."""

    def __init__(self) -> None:
        self._fragments: dict[str, _Fragment] = {}
        self._contributors: list[str] = []

    def load_from_profile(self, profile_path: Path, manifest: ProfileManifest) -> None:
        """Load instruction fragments from a profile and merge them into the chain.

        Args:
            profile_path: Root directory of the profile
            manifest: ProfileManifest for the profile being loaded
        """
        instructions_dir = profile_path / "instructions"
        if not instructions_dir.exists() or not instructions_dir.is_dir():
            raise FileNotFoundError(
                f"Profile '{manifest.name}' must have an 'instructions/' directory. "
                "The old 'instructions.md' format is no longer supported."
            )

        fragment_paths = sorted(
            (path for path in instructions_dir.glob("*.md") if path.is_file()),
            key=lambda path: path.name,
        )

        for fragment_path in fragment_paths:
            content = self._read_fragment_content(fragment_path)
            if not content.strip():
                self._fragments.pop(fragment_path.name, None)
                log.debug(
                    "Fragment '%s' in profile '%s' is empty; removing any inherited version.",
                    fragment_path.name,
                    manifest.name,
                )
                continue

            self._fragments[fragment_path.name] = _Fragment(manifest.name, content)
            if manifest.name not in self._contributors:
                self._contributors.append(manifest.name)
            log.debug(
                "Loaded instruction fragment '%s' from profile '%s'",
                fragment_path.name,
                manifest.name,
            )

    def get_instructions(self) -> str | None:
        """Return the merged instruction text."""
        if not self._fragments:
            return None

        parts = [
            fragment.content
            for _, fragment in sorted(self._fragments.items(), key=lambda item: item[0])
        ]
        return SEPARATOR.join(parts)

    def _read_fragment_content(self, fragment_path: Path) -> str:
        text = fragment_path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            return text

        lines = text.splitlines(keepends=True)
        end_index: int | None = None
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                end_index = index
                break

        if end_index is None:
            raise ValueError(f"YAML front matter in '{fragment_path}' must be closed with '---'.")

        yaml.safe_load("".join(lines[1:end_index]))
        return "".join(lines[end_index + 1 :]).lstrip("\n")

    @property
    def source_profile(self) -> str | None:
        """Profile that most recently contributed non-empty instruction content."""
        if not self._fragments:
            return None
        return self._contributors[-1] if self._contributors else None

    @property
    def source_profiles(self) -> list[str]:
        """Profiles that currently contribute at least one fragment, in load order."""
        if not self._fragments:
            return []
        return list(self._contributors)
