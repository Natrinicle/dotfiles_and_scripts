---
paths:
  - "**/*.py"
  - "**/pyproject.toml"
  - "**/requirements*.txt"
---

# Python

- After edits: `ruff check --fix` and `ruff format` when available
- Type-check with `pyright` or `mypy` when the project uses them
- Annotate public function signatures
- Prefer `pathlib.Path` over string path math
- Use `subprocess.run([...])` without `shell=True` for untrusted data
- Pin deps in lock/requirements files for apps; use ranges carefully in libraries
