---
name: speakr-scanner
description: >
  Extract high-confidence Speakr speech segments for writing-style and contact
  analysis. Read-only against the Speakr DB; invokes style-analyzer and contact-syncer.
---

# Speakr Scanner

Pull **resolved** speech from Speakr into analysis pipelines. This skill is
**read-only** on the Speakr database. All attribution fixes belong in
`speakr-manage`.

When `profile-updater` calls this skill, run **pull-only** (skip analysis
invocations).

## Pre-flight

```bash
test -f "${SPEAKR_DB:-$HOME/docker/speakr/instance/transcriptions.db}"
```

Default API/DB layout matches a dockerized Speakr under `$HOME/docker/speakr`.
Override with `SPEAKR_DB` / API base env vars when installs differ.

## Transcript shape

`recording.transcription` is a JSON array of segments:

```json
[
  {"speaker": "Full Name", "sentence": "…", "start_time": 3.76, "end_time": 4.36}
]
```

Unresolved speakers still look like `SPEAKER_00`. Prefer recordings
`speakr-manage` already processed (IDs listed in manage state).

## Gotcha: no `modified_at` — hash the body

Speakr often has no reliable modified timestamp. Track content hashes in
`{MEMORY_ROOT}/speakr-scanner-hashes.json`:

```json
{ "12": { "hash": "md5…", "last_scanned": "YYYY-MM-DD" } }
```

Each run (14-day window, completed, long enough transcript):

1. MD5 the transcription text  
2. Missing hash → new; matching hash → skip; different hash → **re-extract**  
   (covers speaker renames, hotword fixes, retranscriptions)  
3. Prune hash entries with `last_scanned` older than 14 days  

Without hashing, re-attribution weeks later never reaches style/contact tools.

## Confidence filter

Skip low-value rows:

- Not in manage’s `processed` list (optional but recommended)  
- More than ~20% of segments still `SPEAKER_\d+` **and** the user’s segments
  are unresolved → skip whole recording  
- If the user is labeled but others are not, still export the user’s lines;
  omit unresolved speakers from contact export  

## Extraction

Cache under `~/.cache/agent-pulls/speakr/` (or `~/.firecrawl/speakr/` if that
tree already exists on the machine).

### User segments → `speakr-my-segments.json`

Normalized messages:

```json
[{"ts": "…", "text": "…", "source": "speakr", "channel": "recording-{id}", "audience": "meeting-1on1"}]
```

**Merge** consecutive same-speaker lines until another speaker, a >5s gap, or a
clear topic break. Audience by distinct speaker count: 2 → `meeting-1on1`,
3–5 → `meeting-small-group`, 6+ → `meeting-large`.

Identify the user by full name and aliases from the writing-style profile —
never hardcode a personal name in the skill.

### Coworkers → `speakr-coworker-segments.json`

Group by resolved speaker name. Feeds spoken-vs-written tone and meeting
dynamics into `contact-syncer`.

### Meetings → `speakr-meetings.json`

Per recording: id, title, date, participants, duration, talk ratios.

## Analysis (unless pull-only)

1. **`style-analyzer`** on user segments  
   - Weight below typed chat (ASR + diarization error)  
   - Do **not** promote um/uh fillers into written style unless they appear in
     verified text too  
   - Looser fragments and restarts are normal speech  
   - May add a provisional “meeting speech” audience mode  

2. **`contact-syncer`** on the pull directory  
   - Spoken friction can differ from ticket/chat tone  
   - Talk ratio is a weak relationship signal, not a judgment  

## Privacy

Recordings stay local. Do not commit pull caches or tokens. Re-processing a
changed hash rebuilds combined exports from all qualifying recordings (not a
blind append of duplicates without overwrite of that recording’s prior extract).
