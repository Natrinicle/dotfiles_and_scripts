"""Configuration loading for mempalace-router targets."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml


class ConfigError(ValueError):
    """Raised when configuration is invalid."""


@dataclass(frozen=True)
class Target:
    """A single routing target."""

    name: str
    kind: Literal["local", "company"]
    company: str | None
    url: str | None
    token_file: Path | None
    palace_path: Path | None
    hints: dict[str, list[str]]


DEFAULT_SINGLE_VALUED_PREDICATES = ("version", "interface_kind", "reach", "status")


@dataclass
class Targets:
    """All loaded targets.

    ``single_valued_predicates`` is the allowlist of KG predicates for which
    a read-time conflict between local and company may be corrected (the
    older side superseded). Conflicts on any other predicate are reported
    only.
    """

    by_name: dict[str, Target]
    local: Target
    companies: dict[str, Target]
    single_valued_predicates: frozenset[str] = field(
        default_factory=lambda: frozenset(DEFAULT_SINGLE_VALUED_PREDICATES)
    )

    def get(self, name: str) -> Target:
        """Get a target by name, raising KeyError if not found."""
        return self.by_name[name]


DEFAULT_CONFIG_PATH = Path("~/.config/mempalace-router/targets.yaml").expanduser()


def normalize_hub_url(url: str) -> str:
    """Return a hub base URL: strip trailing ``/`` and one trailing ``/mcp``.

    Clients append ``/mcp`` and ``/healthz`` themselves, while users usually
    copy the full ``.../mcp`` endpoint from an MCP client config.
    """
    base = url.rstrip("/")
    if base.endswith("/mcp"):
        base = base[: -len("/mcp")].rstrip("/")
    return base


def _single_valued(value) -> frozenset[str]:
    if value is None:
        return frozenset(DEFAULT_SINGLE_VALUED_PREDICATES)
    if not isinstance(value, list) or not all(isinstance(p, str) and p for p in value):
        raise ConfigError("'single_valued_predicates' must be a list of non-empty strings")
    return frozenset(value)


def _validate_hints(hints_value, target_name: str) -> dict[str, list[str]]:
    """Validate and normalize hints field.

    Returns empty dict if absent or null.
    Raises ConfigError if not a dict with list values.
    """
    if hints_value is None:
        return {}
    if not isinstance(hints_value, dict):
        raise ConfigError(f"Target '{target_name}' hints must be a dict, got {type(hints_value).__name__}")
    for key, value in hints_value.items():
        if not isinstance(value, list):
            raise ConfigError(
                f"Target '{target_name}' hints['{key}'] must be a list, got {type(value).__name__}"
            )
        for item in value:
            if not isinstance(item, str):
                raise ConfigError(
                    f"Target '{target_name}' hints['{key}'] contains non-string item: {type(item).__name__}"
                )
    return hints_value


def load_targets(path: Path) -> Targets:
    """Load targets from a YAML file.

    The YAML file must have a 'targets' dict at the root, where each key
    is a target name and value is a target definition.

    A local target may give either (url + token_file) or palace_path.
    A company target must have company, url, and token_file.
    Exactly one local target is required.

    ~ and $HOME are expanded in token_file and palace_path. ``url`` is
    normalised to the hub base (a trailing ``/mcp`` is dropped).

    An optional top-level ``single_valued_predicates`` list sets the KG
    predicates eligible for read-time correction (default
    ``DEFAULT_SINGLE_VALUED_PREDICATES``).

    Raises ConfigError if validation fails.
    """
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except FileNotFoundError as e:
        raise ConfigError(f"Config file not found: {path}") from e
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {path}: {e}") from e

    if not isinstance(data, dict) or "targets" not in data:
        raise ConfigError("YAML must have a 'targets' key at root")

    targets_data = data["targets"]
    if not isinstance(targets_data, dict):
        raise ConfigError("'targets' must be a dict")

    by_name = {}
    local_targets = []
    company_targets = {}

    for name, target_data in targets_data.items():
        if not isinstance(target_data, dict):
            raise ConfigError(f"Target '{name}' must be a dict")

        kind = target_data.get("kind")
        if kind not in ("local", "company"):
            raise ConfigError(f"Target '{name}' has unknown kind: {kind}")

        # Handle common fields
        url = target_data.get("url")
        if isinstance(url, str) and url:
            url = normalize_hub_url(url)
        token_file_raw = target_data.get("token_file")
        palace_path_raw = target_data.get("palace_path")
        hints_raw = target_data.get("hints")

        # Expand ~ and $HOME in paths only
        if token_file_raw:
            token_file = Path(token_file_raw).expanduser()
            token_file = Path(os.path.expandvars(str(token_file)))
        else:
            token_file = None

        if palace_path_raw:
            palace_path = Path(palace_path_raw).expanduser()
            palace_path = Path(os.path.expandvars(str(palace_path)))
        else:
            palace_path = None

        if kind == "local":
            # Local target must not have company field
            if target_data.get("company") is not None:
                raise ConfigError(f"Local target '{name}' cannot have 'company' field")

            # Local target: must have (url + token_file) or palace_path
            if (url and token_file) or palace_path:
                if url and token_file and palace_path:
                    raise ConfigError(
                        f"Local target '{name}' cannot have both (url+token_file) and palace_path"
                    )
            else:
                raise ConfigError(
                    f"Local target '{name}' must have (url + token_file) or palace_path"
                )

            hints = _validate_hints(hints_raw, name)
            target = Target(
                name=name,
                kind="local",
                company=None,
                url=url,
                token_file=token_file,
                palace_path=palace_path,
                hints=hints,
            )
            local_targets.append(target)
            by_name[name] = target

        elif kind == "company":
            # Company target must not have palace_path field
            if palace_path_raw is not None:
                raise ConfigError(f"Company target '{name}' cannot have 'palace_path' field")

            # Company target: must have company, url, and token_file
            company = target_data.get("company")
            if not company:
                raise ConfigError(f"Company target '{name}' must have 'company' field")
            if not url:
                raise ConfigError(f"Company target '{name}' must have 'url' field")
            if not token_file:
                raise ConfigError(f"Company target '{name}' must have 'token_file' field")

            hints = _validate_hints(hints_raw, name)
            target = Target(
                name=name,
                kind="company",
                company=company,
                url=url,
                token_file=token_file,
                palace_path=None,
                hints=hints,
            )
            company_targets[name] = target
            by_name[name] = target

    # Validate exactly one local target
    if len(local_targets) != 1:
        raise ConfigError(f"Must have exactly one local target; found {len(local_targets)}")

    return Targets(
        by_name=by_name,
        local=local_targets[0],
        companies=company_targets,
        single_valued_predicates=_single_valued(data.get("single_valued_predicates")),
    )
