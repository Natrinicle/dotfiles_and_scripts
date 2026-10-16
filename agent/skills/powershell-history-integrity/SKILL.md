---
name: powershell-history-integrity
description: "Thin companion to shell-history-integrity for Windows PowerShell / PSReadLine history. Apply the same integrity checks to ConsoleHost_history.txt and Clear-History patterns."
type: knowledge
lifecycle: active
---

# PowerShell History Integrity

Thin companion to `shell-history-integrity`.

## Core reuse

Follow the same indicator approach: empty or truncated history on an active account is a signal, not proof.

## Windows additions

- PSReadLine history: `%APPDATA%\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt` (no per-command timestamps by default).
- `Clear-History`, `Remove-Item` of the history file, or `Set-PSReadLineOption -HistorySaveStyle SaveNothing`.
- Correlate with UserAssist, Prefetch, or 4688 for activity that should have generated history.

## Output

Same `HISTORY_INTEGRITY` block; add `shell: powershell|pwsh`.

## Upstream note

Conclusion field and “indicator not proof” stance must stay compatible.
