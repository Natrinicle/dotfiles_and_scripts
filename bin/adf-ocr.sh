#!/usr/bin/env bash
# =============================================================================
# EPSON ES-C320W ADF Scanner → Multi-Load + Local LLM + Robust Naming + Full Cleanup
# =============================================================================

set -euo pipefail

# -------------------------- Required packages --------------------------
# sudo apt update && sudo apt install -y \
#     sane-utils tesseract-ocr tesseract-ocr-eng imagemagick \
#     img2pdf ocrmypdf bc poppler-utils exiftool jq

# -------------------------- User Settings --------------------------
SCAN_MODE="Color"
SCAN_RESOLUTION=300
SCAN_FORMAT="png"

MULTI_LOAD_TIMEOUT=30

# Blank page removal (forgiving for uneven pages)
MARGIN_TO_SHAVE=80
BLUR_RADIUS=12
FUZZ_PERCENT=20%
MIN_CONTENT_WIDTH=120
MIN_CONTENT_HEIGHT=80

DEBUG_BLANK=false

# -------------------------- LLM Settings --------------------------
LLM_SERVER_URL="http://127.0.0.1:11434/v1/chat/completions"
LLM_MODEL="gemma4:e2b"
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2000
# =============================================================================

find_epson_device() {
    local device
    device=$(scanimage -L 2>/dev/null | grep -o 'escl:https\?://[^ ]*EPSON ES-C320W' | head -n1 || echo "")
    [ -n "$device" ] && { echo "$device"; return 0; }
    device=$(scanimage -L 2>/dev/null | grep -o 'airscan:[^:]*:EPSON ES-C320W' | head -n1 || echo "")
    [ -n "$device" ] && { echo "$device"; return 0; }
    device=$(scanimage -L 2>/dev/null | grep -o 'escl:[^ ]*EPSON ES-C320W' | head -n1 || echo "")
    echo "$device"
}

count_pages() {
    ls page_*."${SCAN_FORMAT}" 2>/dev/null | wc -l | tr -d '[:space:]' || echo 0
}

# -------------------------- Main Script --------------------------
echo "=== EPSON ES-C320W Continuous Multi-Load Scanner with AI Naming ==="

WORK_DIR="$(pwd)/scan_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

if command -v curl >/dev/null 2>&1; then
    echo "=== Preloading ${LLM_MODEL} LLM ==="
    curl -s -X POST "$LLM_SERVER_URL" -H "Content-Type: application/json" -d '{"model": "'"$LLM_MODEL"'"}' >/dev/null 2>&1
fi

echo "=== Starting continuous ADF scan ==="

last_successful_scan=$(date +%s)

while true; do
    SCAN_DEVICE=$(find_epson_device)
    if [ -z "$SCAN_DEVICE" ]; then
        echo "ERROR: Could not find EPSON ES-C320W."
        exit 1
    fi

    SOURCE_OUTPUT=$(scanimage -d "$SCAN_DEVICE" --help 2>/dev/null | grep -i -- --source || echo "")
    if [ -z "$SOURCE_OUTPUT" ]; then
        SELECTED_SOURCE="Automatic Document Feeder"
    else
        POSSIBLE_SOURCES=$(echo "$SOURCE_OUTPUT" | sed 's/.*--source *//' | tr '|' '\n' | sed 's/ *\[[^]]*\].*//; s/^[[:space:]]*//; s/[[:space:]]*$//')
        SELECTED_SOURCE=$(echo "$POSSIBLE_SOURCES" | grep -i "duplex" | head -n1 || echo "")
        [ -z "$SELECTED_SOURCE" ] && SELECTED_SOURCE=$(echo "$POSSIBLE_SOURCES" | grep -i "ADF" | head -n1 || echo "Automatic Document Feeder")
    fi

    old_count=$(count_pages)

    scanimage --batch=page_%04d.${SCAN_FORMAT} --format=${SCAN_FORMAT} \
        --mode=${SCAN_MODE} --resolution=${SCAN_RESOLUTION} --batch-count=0 \
        --batch-start=$((old_count + 1)) -d "$SCAN_DEVICE" --source="${SELECTED_SOURCE}" 2>&1 || true

    new_count=$(count_pages)
    scanned_this_batch=$((new_count - old_count))

    if [ "$scanned_this_batch" -gt 0 ]; then
        echo "   ✓ Scanned ${scanned_this_batch} page(s)"
        last_successful_scan=$(date +%s)
    else
        echo "   ADF appears empty."
    fi

    current_time=$(date +%s)
    if [ $((current_time - last_successful_scan)) -ge $MULTI_LOAD_TIMEOUT ]; then
        echo "   Timeout reached. Proceeding..."
        break
    fi
    sleep 5
done

# -------------------------- Processing --------------------------
mapfile -t pages < <(printf '%s\n' page_*."${SCAN_FORMAT}" 2>/dev/null | sort -V)

processed=()
for img in "${pages[@]}"; do
    if convert "$img" -shave 80x80 -virtual-pixel White -blur 0x12 -fuzz 20% -trim -format "%wx%h" info: 2>/dev/null | \
       awk -F'x' '{if($1<120 || $2<80) exit 0; else exit 1}'; then
        echo "→ Removing blank page: $img"
        rm -f "$img"
        continue
    fi
    processed+=("$img")
done

img2pdf "${processed[@]}" -o intermediate.pdf
ocrmypdf --language eng --rotate-pages --deskew --clean --optimize 1 --force-ocr intermediate.pdf "temp_ocr.pdf"

# -------------------------- AI Filename + Full Cleanup --------------------------
echo "=== Generating smart filename and metadata ==="

TODAY=$(date +%Y-%m-%d)
NOW=$(date +%H-%M-%S)
base_name="document"
title="Scanned Document"
author="Unknown"
subject="Scanned Document"
keywords="scanned"

if [ -s "temp_ocr.pdf" ] && command -v pdftotext curl jq >/dev/null 2>&1; then
    pdftotext "temp_ocr.pdf" extracted_text.txt 2>/dev/null || true
    if [ -s extracted_text.txt ]; then
        prompt="You are an expert document archivist. Analyze the text below and return **only** valid JSON.

Text:
$(head -c 15000 extracted_text.txt)

Return this exact JSON:
{
  \"base_name\": \"descriptive-filename-using-key-info\",
  \"title\": \"Full clear title\",
  \"author\": \"Company or person or Unknown\",
  \"subject\": \"Document type or short description\",
  \"keywords\": \"comma,separated,keywords\"
}"

        response=$(jq -n \
            --arg model "${LLM_MODEL}" \
            --arg content "${prompt}" \
            --argjson temp ${LLM_TEMPERATURE} \
            --argjson tokens ${LLM_MAX_TOKENS} \
            '{
              model: $model,
              messages: [{role: "user", content: $content}],
              temperature: $temp,
              max_tokens: $tokens
             }' | curl -s -X POST "$LLM_SERVER_URL" \
            -H "Content-Type: application/json" \
            -d @- || echo "{}" 2>/dev/null || echo "{}")

        ai_json=$(echo "$response" | jq -r '.choices[0].message.content' 2>/dev/null || echo "{}")
        # Remove ```json from the beginning and ``` from the end of the response
        ai_json=$(echo "${ai_json}" | sed -e 's/^```json//' -e 's/^```//' -e 's/```$//')

        base_name=$(echo "$ai_json" | jq -r '.base_name // "document"' 2>/dev/null | tr -cd '[:alnum:][:space:]_-' | tr ' ' '_' || echo "document")
        title=$(echo "$ai_json" | jq -r '.title // "Scanned Document"' 2>/dev/null | tr -cd '[:alnum:][:space:]_-' || echo "Scanned Document")
        author=$(echo "$ai_json" | jq -r '.author // "Unknown"' 2>/dev/null | tr -cd '[:alnum:][:space:]_-' || echo "Unknown")
        subject=$(echo "$ai_json" | jq -r '.subject // "Scanned Document"' 2>/dev/null | tr -cd '[:alnum:][:space:]_-' || echo "Scanned Document")
        keywords=$(echo "$ai_json" | jq -r '.keywords // "scanned"' 2>/dev/null | tr -cd '[:alnum:][:space:]_-' || echo "scanned")
    fi
fi

FINAL_FILENAME="${TODAY}_${NOW}_${base_name}.pdf"
FINAL_PDF="../${FINAL_FILENAME}"

echo "→ Moving final PDF to: $FINAL_FILENAME"

if mv -f "temp_ocr.pdf" "$FINAL_PDF"; then
    echo "→ Successfully created final PDF"
else
    echo "ERROR: Failed to move final PDF!"
    exit 1
fi

# Optional: embed metadata with exiftool
exiftool -overwrite_original -Title="${title}" -Author="${author}" -Subject "${subject}" -Keywords "${keywords}" "$FINAL_PDF" 2>/dev/null || true

# Full cleanup
echo "=== Cleaning up temporary directory ==="
cd ..
rm -rf "$WORK_DIR" 2>/dev/null || true

echo "======================================================================"
echo "✅ DONE!"
echo "   Final PDF: $(realpath "$FINAL_PDF" 2>/dev/null || echo "$FINAL_PDF")"
echo "======================================================================"
