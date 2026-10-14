---
paths:
  - "**/*.py"
  - "**/pyproject.toml"
  - "**/requirements*.txt"
---

# Python

- If **pre-commit-gate** applies, that run is the first lint
- After edits: `ruff check --fix` and `ruff format` when available unless pre-commit already ran those hooks on this file
- Type-check with `pyright` or `mypy` when the project uses them
- Annotate public function signatures
- Prefer `pathlib.Path` over string path math
- Use `subprocess.run([...])` without `shell=True` for untrusted data
- Pin deps in lock/requirements files for apps; use ranges carefully in libraries
