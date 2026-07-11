# Check Upstream Before Writing

Before adding code, see whether the capability already exists in:

- Base classes / framework lifecycle hooks
- Official SDKs and instrumentations
- Standard library
- Config options on dependencies you already use

## Habits
1. Read types or docs for the dependency
2. Skim source in the package cache if docs are thin
3. Confirm with a small experiment (actual trace, log, or API output)
4. Search for recent upstream fixes before inventing a wrapper

Avoid pass-through overrides that only call `super`, duplicate middleware the framework already provides, or custom flags when the base type already exposes enable/disable.
