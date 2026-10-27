---
name: speckit
description: Import GitHub Spec Kit locally. Use when the user wants constitution, specify, clarify, checklist, analyze, or converge, or says spec-kit / spec-key / specify init.
---

# Spec Kit (local import)

GitHub `spec-kit` (`specify-cli`) is installed as `specify` on PATH. This
skill imports the **missing** agent commands. Do not duplicate skills that
already cover plan / tasks / implement.

`specify init --integration grok` is unknown. Use `--integration claude` in
a real project, then follow this dispatcher (Grok skills symlink into the
Claude skill tree).

## Resolve templates

1. `SPECKIT_ROOT` if set
2. `${HOME}/opt/spec-kit`
3. Else `specify --help` and tell the user to `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git`

Command templates: `${SPECKIT_ROOT}/templates/commands/<name>.md`.
Read that file and follow it. Substitute `$ARGUMENTS` with the user text.
Do not paste the whole template into chat.

Init a project (when the user named a directory):

```bash
specify init <project> --integration claude --non-interactive
# or in cwd: specify init --here --force --non-interactive --integration claude
```

`specify integration list` only works inside a Spec Kit project (`.specify/`).

## Command map

| Spec Kit | This pack | Action |
|----------|-----------|--------|
| constitution | **this skill** | Follow `templates/commands/constitution.md` → `.specify/memory/constitution.md` |
| specify | **this skill** | Follow `templates/commands/specify.md` |
| clarify | **this skill** | Follow `templates/commands/clarify.md` (≤5 questions, write answers into the spec) |
| plan | `design` + `writing-plans` | Do not reimplement Spec Kit plan |
| checklist | **this skill** | Follow `templates/commands/checklist.md` (requirements quality, not code tests) |
| tasks | `writing-plans` | Point there |
| analyze | **this skill** | Follow `templates/commands/analyze.md` (spec/plan/tasks consistency) |
| implement | `execute-plan` | Point there |
| converge | **this skill** | Follow `templates/commands/converge.md` (append remaining work to tasks.md) |
| taskstoissues | skip | GitHub issues; only if the user named that |
| bug extension | `bug-finder` | Already present |

## When the user names a Spec Kit verb

1. Confirm cwd is a Spec Kit project, or run `specify init` if they named init.
2. Read the matching template under `templates/commands/`.
3. For plan / tasks / implement, load the mapped existing skill instead of the
   Spec Kit template.
4. After constitution/specify/clarify/checklist/analyze/converge, offer the
   template's handoff (do not auto-invoke implement).

## Anti-patterns

- Scaffolding a dummy project under `${HOME}` just to run `specify integration list`
- Copying Spec Kit `plan`/`tasks`/`implement` templates over `design` /
  `writing-plans` / `execute-plan`
- Hardcoding a personal login or `${HOME}/opt` as the only template path
