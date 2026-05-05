from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)


@dataclass
class PromptDefinition:
    name: str
    content: str
    source_profile: str


@dataclass
class ResourceDefinition:
    uri: str
    name: str
    description: str
    backend_function: str
    backend_params: dict[str, Any] = field(default_factory=dict)
    merge: bool = False


@dataclass
class UdaDefinition:
    name: str
    type: str  # "string" | "numeric" | "date" | "duration"
    label: str = ""
    values: list[str] = field(default_factory=list)
    default: str = ""


@dataclass
class ContextDefinition:
    name: str
    read_filter: str = ""
    write_filter: str = ""


@dataclass
class PromptDeclaration:
    name: str
    file: str  # relative path inside profile dir, e.g. "prompts/code_review.md"


@dataclass
class ReviewConfig:
    projects: list[str] = field(default_factory=list)
    default_project: str = ""
    include_no_project: bool = False


@dataclass
class ProfileManifest:
    name: str
    version: str
    description: str = ""
    author: str = ""
    extends: list[str] = field(default_factory=list)
    udas: list[UdaDefinition] = field(default_factory=list)
    contexts: list[ContextDefinition] = field(default_factory=list)
    review: ReviewConfig = field(default_factory=ReviewConfig)
    resources: list[dict[str, Any]] = field(default_factory=list)
    prompts: list[PromptDeclaration] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    # runtime-attached profile path (set by ProfileManager when loading)
    path: Path | None = None

    @staticmethod
    def from_yaml(path: Path) -> ProfileManifest:
        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError("Profile manifest YAML must contain a mapping")
        if "name" not in data or "version" not in data:
            raise ValueError("Profile manifest YAML must contain 'name' and 'version'")

        # Parse extends: accept string or list[str]
        extends_raw = data.get("extends", [])
        if isinstance(extends_raw, str):
            extends = [extends_raw]
        elif isinstance(extends_raw, list):
            extends = extends_raw
        else:
            extends = []

        # Parse UDAs: top-level 'udas' only (legacy 'requirements.udas' support removed)
        udas_raw = data.get("udas", [])


        udas: list[UdaDefinition] = []
        for uda_entry in udas_raw:
            if isinstance(uda_entry, dict):
                # Ensure a label is always present: if none provided, derive from name
                name_val = uda_entry.get("name", "")
                label_val = uda_entry.get("label", "") or ""
                if not label_val and name_val:
                    # Capitalize only the first character, keep the rest as-is
                    label_val = name_val[0].upper() + name_val[1:]
                udas.append(
                    UdaDefinition(
                        name=name_val,
                        type=uda_entry.get("type", "string"),
                        label=label_val,
                        values=uda_entry.get("values", []),
                        default=uda_entry.get("default", ""),
                    )
                )

        # Parse contexts: accept 'context' or 'contexts'
        contexts_raw = data.get("contexts") or data.get("context") or []
        contexts: list[ContextDefinition] = []
        for ctx_entry in contexts_raw:
            if isinstance(ctx_entry, dict):
                contexts.append(
                    ContextDefinition(
                        name=ctx_entry.get("name", ""),
                        read_filter=ctx_entry.get("read_filter", ""),
                        write_filter=ctx_entry.get("write_filter", ""),
                    )
                )

        # Parse review config
        review_raw = data.get("review", {})
        review = ReviewConfig(
            projects=review_raw.get("projects", []) if isinstance(review_raw, dict) else [],
            default_project=review_raw.get("default_project", "") if isinstance(review_raw, dict) else "",
            include_no_project=review_raw.get("include_no_project", False) if isinstance(review_raw, dict) else False,
        )

        # Parse prompts: entries with 'file' key become PromptDeclaration
        prompts_raw = data.get("prompts", [])
        prompts: list[PromptDeclaration] = []
        for prompt_entry in prompts_raw:
            if isinstance(prompt_entry, dict) and "file" in prompt_entry:
                prompts.append(
                    PromptDeclaration(
                        name=prompt_entry.get("name", ""),
                        file=prompt_entry.get("file", ""),
                    )
                )

        # Parse tools whitelist
        tools_raw = data.get("tools", [])
        tools: list[str] = []
        if isinstance(tools_raw, list):
            tools = [t for t in tools_raw if isinstance(t, str)]

        return ProfileManifest(
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            author=data.get("author", ""),
            extends=extends,
            udas=udas,
            contexts=contexts,
            review=review,
            resources=data.get("resources", []),
            prompts=prompts,
            tools=tools,
        )
