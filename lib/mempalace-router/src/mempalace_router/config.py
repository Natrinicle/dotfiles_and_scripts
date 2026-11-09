"""Configuration loading for mempalace-router targets."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml


class ConfigError(ValueError):
    """Raised when configuration is invalid."""

    pass


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


@dataclass
class Targets:
    """All loaded targets."""

    by_name: dict[str, Target]
    local: Target
    companies: dict[str, Target]

    def get(self, name: str) -> Target:
        """Get a target by name, raising KeyError if not found."""
        return self.by_name[name]


DEFAULT_CONFIG_PATH = Path("~/.config/mempalace-router/targets.yaml").expanduser()


def load_targets(path: Path) -> Targets:
    """Load targets from a YAML file.

    The YAML file must have a 'targets' dict at the root, where each key
    is a target name and value is a target definition.

    A local target may give either (url + token_file) or palace_path.
    A company target must have company, url, and token_file.
    Exactly one local target is required.

    ~ and $HOME are expanded in token_file and palace_path.

    Raises ConfigError if validation fails.
    """
    with open(path) as f:
        data = yaml.safe_load(f)

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
        token_file_raw = target_data.get("token_file")
        palace_path_raw = target_data.get("palace_path")
        hints = target_data.get("hints", {})

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
            # Company target: must have company, url, and token_file
            company = target_data.get("company")
            if not company:
                raise ConfigError(f"Company target '{name}' must have 'company' field")
            if not url:
                raise ConfigError(f"Company target '{name}' must have 'url' field")
            if not token_file:
                raise ConfigError(f"Company target '{name}' must have 'token_file' field")

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
    )
