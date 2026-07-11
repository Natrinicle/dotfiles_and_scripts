# Config Drop-in Directories

When a service supports `*.d/` / `config.d/` fragments, put custom config there instead of editing the main file.

## Exceptions
Some files use a different root element or load path and cannot live in the merge directory. Document those with a comment and the correct load path.

## Habits
- One concern per fragment file
- Prefer read-only mounts for config in containers
- Prefer separate files over a growing monolith
