#!/usr/bin/env bash
# Continuous ADF capture → blank-page filter → OCR PDF → optional local LLM title.
# Tuned for SANE-accessible document scanners (EPSON ES-C320W among others).
#
# Dependencies (typical):
#   sane-utils tesseract-ocr imagemagick img2pdf ocrmypdf poppler-utils
#   curl jq exiftool (optional LLM + metadata)
#
# Env overrides:
#   ADF_DEVICE_MATCH   grep pattern for scanimage -L (default: EPSON|ADF)
#   LLM_SERVER_URL     OpenAI-compatible chat completions URL
#   LLM_MODEL          model name

set -euo pipefail

SCAN_MODE=${SCAN_MODE:-Color}
SCAN_RESOLUTION=${SCAN_RESOLUTION:-300}
SCAN_FORMAT=${SCAN_FORMAT:-png}
IDLE_SECONDS=${MULTI_LOAD_TIMEOUT:-30}
DEVICE_MATCH=${ADF_DEVICE_MATCH:-'EPSON|ES-C320W|ADF'}

LLM_URL=${LLM_SERVER_URL:-http://127.0.0.1:8080/v1/chat/completions}
LLM_MODEL=${LLM_MODEL:-gemma-3-12b-it}

pick_device() {
  local listing line
  listing=$(scanimage -L 2>/dev/null || true)
  while IFS= read -r line; do
    if printf '%s\n' "$line" | grep -Eqi "$DEVICE_MATCH"; then
      # device id is the backtick-quoted token
      printf '%s\n' "$line" | grep -oP '`\K[^`]+' | head -1
      return 0
    fi
  done <<<"$listing"
  return 1
}

page_count() {
  ls page_*."${SCAN_FORMAT}" 2>/dev/null | wc -l | tr -d ' '
}

is_mostly_blank() {
  local img=$1 dims
  dims=$(
    convert "$img" -shave 80x80 -virtual-pixel White -blur 0x12 -fuzz 20% -trim \
      -format '%w %h' info: 2>/dev/null || echo "0 0"
  )
  # shellcheck disable=SC2086
  set -- $dims
  local w=${1:-0} h=${2:-0}
  ((w < 120 || h < 80))
}

echo "ADF scan → OCR pipeline"

work=$(pwd)/scan_$(date +%Y%m%d_%H%M%S)
mkdir -p "$work"
cd "$work"

last_ok=$(date +%s)

while true; do
  dev=$(pick_device || true)
  if [[ -z ${dev:-} ]]; then
    echo "error: no scanner matching /${DEVICE_MATCH}/ from scanimage -L" >&2
    exit 1
  fi

  source_help=$(scanimage -d "$dev" --help 2>/dev/null || true)
  source_arg="Automatic Document Feeder"
  if printf '%s' "$source_help" | grep -q -- '--source'; then
    if printf '%s' "$source_help" | grep -qi duplex; then
      source_arg=$(printf '%s' "$source_help" | grep -oP -- '--source.*?\|?\K[^| ]*[Dd]uplex[^| ]*' | head -1 || true)
    fi
    if [[ -z ${source_arg:-} ]] || [[ $source_arg == "Automatic Document Feeder" ]]; then
      source_arg=$(printf '%s' "$source_help" | grep -oP -- '--source *\K[^ ]+' | head -1 || echo "ADF")
    fi
  fi

  before=$(page_count)
  scanimage --batch="page_%04d.${SCAN_FORMAT}" --format="$SCAN_FORMAT" \
    --mode="$SCAN_MODE" --resolution="$SCAN_RESOLUTION" --batch-count=0 \
    --batch-start=$((before + 1)) -d "$dev" --source="$source_arg" 2>&1 || true
  after=$(page_count)
  gained=$((after - before))

  if ((gained > 0)); then
    echo "  captured ${gained} page(s) (device ${dev})"
    last_ok=$(date +%s)
  else
    echo "  feeder empty or no new pages"
  fi

  now=$(date +%s)
  if (((now - last_ok) >= IDLE_SECONDS)); then
    echo "  idle ${IDLE_SECONDS}s — finishing capture loop"
    break
  fi
  sleep 5
done

mapfile -t pages < <(printf '%s\n' page_*."${SCAN_FORMAT}" 2>/dev/null | sort -V)
keep=()
for page in "${pages[@]:-}"; do
  [[ -f $page ]] || continue
  if is_mostly_blank "$page"; then
    echo "  drop blank: $page"
    rm -f "$page"
    continue
  fi
  keep+=("$page")
done

if ((${#keep[@]} == 0)); then
  echo "error: no non-blank pages" >&2
  cd ..
  rm -rf "$work"
  exit 1
fi

img2pdf "${keep[@]}" -o intermediate.pdf
ocrmypdf --language eng --rotate-pages --deskew --clean --optimize 1 --force-ocr \
  intermediate.pdf ocr.pdf

base_name=document
today=$(date +%Y-%m-%d)
stamp=$(date +%H-%M-%S)

if command -v pdftotext curl jq >/dev/null 2>&1; then
  pdftotext ocr.pdf text_excerpt.txt 2>/dev/null || true
  if [[ -s text_excerpt.txt ]]; then
    excerpt=$(head -c 4000 text_excerpt.txt | tr '\n' ' ')
    payload=$(jq -n \
      --arg model "$LLM_MODEL" \
      --arg excerpt "$excerpt" \
      '{
        model: $model,
        temperature: 0.3,
        messages: [
          {role: "system", content: "Reply with JSON only: {\"base_name\": \"short_snake_case_title\"}. No punctuation except underscores."},
          {role: "user", content: ("Suggest a short filename stem for this document:\n" + $excerpt)}
        ]
      }')
    if resp=$(curl -sS "$LLM_URL" -H 'Content-Type: application/json' -d "$payload" 2>/dev/null); then
      content=$(printf '%s' "$resp" | jq -r '.choices[0].message.content // empty' 2>/dev/null || true)
      if [[ -n $content ]]; then
        # tolerate fenced JSON
        json_bit=$(printf '%s' "$content" | sed -n '/{/,/}/p' | tr '\n' ' ')
        stem=$(printf '%s' "$json_bit" | jq -r '.base_name // empty' 2>/dev/null || true)
        if [[ -n $stem && $stem != null ]]; then
          base_name=$(printf '%s' "$stem" | tr -cd '[:alnum:]_ -' | tr ' ' '_' | cut -c1-60)
        fi
      fi
    fi
  fi
fi

[[ -z $base_name ]] && base_name=document
final_name="${today}_${stamp}_${base_name}.pdf"
dest="../${final_name}"
mv -f ocr.pdf "$dest"
command -v exiftool >/dev/null 2>&1 &&
  exiftool -overwrite_original -Title="Scanned Document" -Author="Scanner" "$dest" >/dev/null 2>&1 || true

cd ..
rm -rf "$work"
echo "done: $(realpath "$dest" 2>/dev/null || echo "$dest")"
