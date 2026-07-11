#!/usr/bin/env bash
# Launch the pack's voice-recorder entrypoint (same directory).
# Prefer a dedicated venv via VR_PYTHON if set; otherwise python3 on PATH.
#
# Example:
#   python3 -m venv ~/.venvs/voice-recorder
#   ~/.venvs/voice-recorder/bin/pip install -r requirements-voice-recorder.txt
#   VR_PYTHON=~/.venvs/voice-recorder/bin/python3 run-voice-recorder.sh

set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
app=${VOICE_RECORDER_SCRIPT:-${here}/voice-recorder}
py=${VR_PYTHON:-python3}

if [[ ! -f $app ]]; then
  echo "run-voice-recorder: app not found at ${app}" >&2
  exit 1
fi

if ! command -v "$py" >/dev/null 2>&1 && [[ ! -x $py ]]; then
  echo "run-voice-recorder: interpreter not found: ${py}" >&2
  exit 1
fi

exec "$py" "$app" "$@"
