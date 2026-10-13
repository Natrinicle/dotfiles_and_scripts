---
name: bug-skeptic
description: >
  Use when independently proving a bug report or a patch is wrong, rejecting
  hallucinated findings, or running competitive review against finder or
  patcher output.
---

# Bug skeptic

Your job is to **prove the claim wrong**. Default `false` unless you
independently reproduced it.

**REQUIRED BACKGROUND:** **find-patch-loop**.
Do not reuse the finder or patcher conversation. Fresh spawn, fresh context.

## Against a report

Read the queue item. Re-run `repro` yourself. Open the cited files.

| Verdict | When |
|---------|------|
| `real` | You saw the failure with your own command output |
| `false` | Repro does not fail, evidence is invented, or it is a style nit |
| `needs-info` | Hardware, data, or a secret you cannot reach |

`find-patch-queue set ID --skeptic real|false|needs-info --reason '...'`

Failed skeptic spawn → treat as unverified, not as `real`.

## Against a patch

Re-run the **original** repro and the finder's test. Status `verified` only
when that failure is gone and you did not introduce an obvious adjacent
break (run the package tests).

```bash
find-patch-queue set ID --verify fixed --reason 'repro now exits 0'
find-patch-queue set ID --verify still-open --reason 'original repro still fails'
```

Do not use `--skeptic false` on a patched id (that rejects the original
report). Use `--verify still-open` to requeue.

Competitive review (several skeptics on one patch) is allowed. A split vote
without evidence is `needs-info`, not `verified`.

## Do not

- Rubber-stamp because the finder sounded sure.
- Invent extra nits to look busy.
- Apply a further patch. File a new `reported` item instead.
- Be the same agent that filed or patched the id.
