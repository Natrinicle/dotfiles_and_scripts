---
name: speakr-manage
description: >
  Post-process Speakr recordings — speaker labels, domain vocabulary, failed jobs,
  action items, and polling. Use for /speakr-manage, check, or poll modes.
---

# Speakr Manage

Operate a local [Speakr](https://github.com/) (or compatible) stack: correct
speaker attribution, fix ASR vocabulary, recover failed jobs, and extract
action items. Prefer the **HTTP API** for writes; treat SQLite as read-mostly.

## Modes

| Mode | Intent |
|------|--------|
| Full scan | Everything that needs attention |
| `check` | Incremental since last poll (loop-friendly) |
| `poll` | Schedule recurring `check` (e.g. every few minutes) |

## Pre-flight

Fail soft if the stack is down:

1. Cloud credentials only if *your* install needs them for ASR/helpers  
2. Speakr container (or process) is up  
3. WhisperX / ASR sidecar answers on its health port (commonly `9000`)  
4. API base reachable (default `http://localhost:8899/api/v1`)

State lives under `{PROJECT_MEMORY}/speakr-manage-state.md` (processed IDs,
queue, in-flight retranscription). API token: `{MEMORY_ROOT}/speakr-api-token.txt`.
DB path: `$SPEAKR_DB` (default `${HOME}/docker/speakr/instance/transcriptions.db`).

**PATH helpers (install from this repo’s `bin/`):** `speakr-api`, `speakr-poll`,
`speakr-notes-append`. Never hardcode a vendor scripts directory.

## Gotcha: API vs SQLite

| Operation | Use |
|-----------|-----|
| Assign speakers, retitle, re-summarize, re-transcribe, notes | **REST API** (no restart) |
| Cosine match on embeddings, complex multi-recording reads | SQLite **read** while Speakr runs |
| Schema fields the API cannot touch | SQLite **write only after stop** + `PRAGMA wal_checkpoint(TRUNCATE)` + start |

Direct writes without stop/WAL checkpoint corrupt or race the running app.

### Critical: notes replace, they do not append

PATCH/PUT notes endpoints **overwrite**. Always read-merge-write via
`speakr-notes-append` so attribution logs survive.

### Primary write: `speakers/assign`

```bash
speakr-api put recordings/{id}/speakers/assign \
  '{"speaker_map": {"SPEAKER_00": "Full Name"}}'
```

That call renames labels in the transcript JSON, updates the speaker library,
snippets, and participants in one shot. Prefer it over hand-editing JSON.

Useful endpoints (Bearer token):

| Action | Call |
|--------|------|
| Assign speakers | `PUT recordings/{id}/speakers/assign` |
| Re-summarize | `POST recordings/{id}/summarize` |
| Re-transcribe | `POST recordings/{id}/transcribe` |
| Status | `GET recordings/{id}/status` |
| Transcript | `GET recordings/{id}/transcript` |
| List/update speakers | `GET/POST/PUT speakers…` |

## Triage

Load all recordings; skip IDs in `processed` / `permanently_failed`.

| Bucket | Signal | Action |
|--------|--------|--------|
| New completion | `COMPLETED`, not processed | Full post-process |
| Failed | `FAILED` / “No Audio” titles | Assess retranscribe vs permanent fail |
| Thin transcript | completed but very short text | Partial extract only |
| Stuck | non-terminal status for hours | Alert; do not thrash |
| In-flight | state file has active retranscription | Reconcile status first |

`check` mode: only `id > last_processed` or `meeting_date > last_poll`.

## Speaker identification (gotchas)

### Embeddings are two formats

- **Speaker library** (`speaker.average_embedding`): often **packed binary**  
  `256 × float32` → 1024 bytes (`struct.unpack('256f', raw)`).  
- **Per-recording** (`recording.speaker_embeddings`): usually **JSON**.

Writing library embeddings as JSON strings when the app expects packed floats
silently breaks future matches. Pack on write; accept both on read.

### Matching policy

- Cosine similarity ≥ **0.70** and ≥ **0.05** gap vs second place → auto-assign  
- Top-two within 5% → leave unlabeled  
- Calendar attendees are a **candidate pool**, not a seating chart (order ≠ speaker index; not everyone talks)

### Content-based backup (when voice is weak)

1. **Issue keys** spoken in-segment → look up assignee in Jira (`acli` or API); if they describe *their* work on that key, treat as medium-confidence identity  
2. **Same series** prior meetings (calendar title) — labels do **not** persist across recordings; match by topic continuity, not `SPEAKER_04` equality  
3. **Chat / contact roles** — align “I own the X integration” with known role notes  
4. Discourse cues: direct address after a name, “I reviewed your PR” attributed to the PR author, third-person self-reference mis-labels  

After a solid ID, create/update the library profile so the next meeting auto-matches.

## Vocabulary / hotwords

Maintain a hotword list under memory. Apply **context-aware** fixes only, e.g.:

- “hotel” near tracing jargon → `OTEL`  
- mangled product names near observability → correct product  

Promote a correction to active hotwords after it appears in **≥2** recordings.
Never drop active hotwords casually (regressions are painful). Syncing hotwords
into Speakr settings usually needs a controlled restart + WAL checkpoint.

## Failed jobs & retranscription

Serial queue — **one** heavy retranscription at a time. Write in-flight state
*before* starting.

Escalation ladder (stop when something works):

1. Smaller batch size  
2. Lower precision  
3. Smaller model  
4. CPU instead of GPU/MPS  
5. Re-encode audio (e.g. ffmpeg → mp3)  
6. Mark permanently failed  

After direct DB queue inserts, always WAL checkpoint before bringing Speakr back.

## Attribution sweep (every full run)

After new work, scan **all** completed transcripts for remaining `SPEAKER_\d+`:

1. Voice match (high confidence)  
2. Ticket/content match (medium)  
3. Apply via `speakers/assign`  
4. Append attribution log with `speakr-notes-append` (method + score)  
5. `POST …/summarize` so summaries use real names  
6. Report leftovers with sample lines  

Corrections later: search notes for the wrong name, re-`assign`, re-run
`speakr-scanner`, append a `CORRECTED:` line.

## Calendar

Match events by time window (±15 minutes). Use attendees only as candidates.
Use whatever calendar source the host provides (`CALENDAR_CMD`, ICS URL, or API); keep it optional if absent.

## Action items & handoff

- “I’ll …” → owner is current speaker  
- “Name, can you …” → named owner  
- Decisions: “we decided …” with participants  

Write action items to a memory file morning triage can consume. Update state
(`last_poll`, processed IDs, clear in-flight).

## Integration

- **Writes:** this skill  
- **Read-only speech export for style/contacts:** `speakr-scanner`  
- **Ticket lookup for content ID:** `jira-scanner` / `acli`  
- **Chat context:** chat scanner when available  
