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

# Match SANE *description* (device ids are often just escl:https://IP:443).
SCANNER_MATCH="${SCANNER_MATCH:-ES-C320W}"
# Skip scanimage -L when set (exact SANE id, e.g. escl:https://192.168.49.2:443).
ADF_OCR_DEVICE="${ADF_OCR_DEVICE:-}"
# Prefer ADF Duplex when the backend advertises it; falls back to simplex escl.
SCAN_DUPLEX="${SCAN_DUPLEX:-true}"
# Tesseract OSD on this ADF often reports 11–17 on already-upright pages.
# ocrmypdf default is 14; 12 still ignores the ~11 cluster and applies the 13+ cluster.
OCR_ROTATE_THRESHOLD="${OCR_ROTATE_THRESHOLD:-12}"

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

SCAN_DEVICE=""
SELECTED_SOURCE=""
FAILED_DEVICES=()

device_is_failed() {
    local d
    for d in "${FAILED_DEVICES[@]+"${FAILED_DEVICES[@]}"}"; do
        [[ "$d" == "$1" ]] && return 0
    done
    return 1
}

list_sane_device_lines() {
    # escl may dump the scanner HTML UI on stdout; only keep SANE device rows.
    scanimage -L 2>/dev/null | grep -E "^device \`" || true
}

sane_id_from_line() {
    sed -n "s/^device \`\\(.*\\)' is a .*/\\1/p"
}

sane_desc_from_line() {
    sed -n "s/^device \`.*' is a \\(.*\\)/\\1/p"
}

backend_rank() {
    case "$1" in
    escl:*) echo 1 ;;
    airscan:*) echo 2 ;;
    epson2:*) echo 9 ;;
    *) echo 5 ;;
    esac
}

source_candidates() {
    local help_line rest
    help_line=$(scanimage -d "$1" --help 2>/dev/null | grep -E '^[[:space:]]*--source ' | head -n1 || true)
    [[ -z "$help_line" ]] && return 0
    rest=${help_line#*--source }
    rest=${rest%%\[*}
    printf '%s\n' "$rest" | tr '|' '\n' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' |
        grep -v '^$' | grep -vi 'no_stringlist' || true
}

choose_source() {
    local token duplex="" adf=""
    while IFS= read -r token; do
        [[ -z "$token" ]] && continue
        case "$token" in
        "ADF Duplex") duplex="$token" ;;
        ADF) adf="$token" ;;
        esac
    done < <(source_candidates "$1")
    if [[ "${SCAN_DUPLEX}" == true && -n "$duplex" ]]; then
        printf '%s\n' "$duplex"
        return 0
    fi
    if [[ -n "$adf" ]]; then
        printf '%s\n' "$adf"
        return 0
    fi
    # Do not invent "Automatic Document Feeder" — airscan rejects it (Invalid argument).
}

probe_scan_device() {
    local device=$1 source=${2:-}
    if [[ -n "$source" ]]; then
        scanimage -n -d "$device" --source "$source" >/dev/null 2>&1
    else
        scanimage -n -d "$device" >/dev/null 2>&1
    fi
}

pick_scanner() {
    local line id desc source rank
    local best_id="" best_source="" best_rank=99

    if [[ -n "${ADF_OCR_DEVICE}" ]]; then
        SCAN_DEVICE="${ADF_OCR_DEVICE}"
        SELECTED_SOURCE=$(choose_source "$SCAN_DEVICE" || true)
        if probe_scan_device "$SCAN_DEVICE" "$SELECTED_SOURCE"; then
            echo "=== Using ${SCAN_DEVICE}${SELECTED_SOURCE:+ --source ${SELECTED_SOURCE}} ==="
            return 0
        fi
        echo "ERROR: ADF_OCR_DEVICE=${ADF_OCR_DEVICE} failed a dry-run open."
        return 1
    fi

    echo "=== Detecting ${SCANNER_MATCH} (one scanimage -L) ==="
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        desc=$(printf '%s\n' "$line" | sane_desc_from_line)
        if ! grep -qi "${SCANNER_MATCH}" <<<"${desc}"; then
            continue
        fi
        id=$(printf '%s\n' "$line" | sane_id_from_line)
        [[ -z "$id" ]] && continue
        if device_is_failed "$id"; then
            echo "   skip ${id} (failed earlier this run)"
            continue
        fi
        source=$(choose_source "$id" || true)
        rank=$(backend_rank "$id")
        if [[ "${SCAN_DUPLEX}" == true && "$source" == "ADF Duplex" ]]; then
            rank=0
        fi
        if ! probe_scan_device "$id" "$source"; then
            echo "   skip ${id}${source:+ --source ${source}} (dry-run failed)"
            continue
        fi
        if ((rank < best_rank)); then
            best_rank=$rank
            best_id=$id
            best_source=$source
        fi
    done < <(list_sane_device_lines)

    if [[ -z "$best_id" ]]; then
        echo "ERROR: Could not find a working ${SCANNER_MATCH} scanner."
        return 1
    fi
    SCAN_DEVICE=$best_id
    SELECTED_SOURCE=$best_source
    echo "=== Using ${SCAN_DEVICE}${SELECTED_SOURCE:+ --source ${SELECTED_SOURCE}} ==="
}

count_pages() {
    local files
    shopt -s nullglob
    files=(page_*."${SCAN_FORMAT}")
    shopt -u nullglob
    printf '%s\n' "${#files[@]}"
}

# -------------------------- Main Script --------------------------
echo "=== EPSON ES-C320W Continuous Multi-Load Scanner with AI Naming ==="

if ! command -v scanimage >/dev/null 2>&1; then
    echo "ERROR: scanimage not found (install sane-utils)."
    exit 1
fi

if ! pick_scanner; then
    exit 1
fi

WORK_DIR="$(pwd)/scan_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

if command -v curl >/dev/null 2>&1; then
    echo "=== Preloading ${LLM_MODEL} LLM ==="
    curl -s -X POST "$LLM_SERVER_URL" -H "Content-Type: application/json" -d '{"model": "'"$LLM_MODEL"'"}' >/dev/null 2>&1
fi

echo "=== Starting continuous ADF scan ==="

last_successful_scan=""

while true; do
    if [[ -z "${SCAN_DEVICE}" ]]; then
        if ! pick_scanner; then
            echo "Retrying scanner detection in 2s..."
            sleep 2
            continue
        fi
    fi

    old_count=$(count_pages)

    scan_cmd=(
        scanimage
        --batch="page_%04d.${SCAN_FORMAT}"
        --format="${SCAN_FORMAT}"
        --mode="${SCAN_MODE}"
        --resolution="${SCAN_RESOLUTION}"
        --batch-count=0
        --batch-start="$((old_count + 1))"
        -d "${SCAN_DEVICE}"
    )
    if [[ -n "${SELECTED_SOURCE}" ]]; then
        scan_cmd+=(--source="${SELECTED_SOURCE}")
    fi

    scan_err=$(mktemp)
    if ! "${scan_cmd[@]}" 2>"$scan_err"; then
        if grep -qiE 'invalid argument|error during device i/o|device busy' "$scan_err"; then
            echo "   Scan failed ($(tr '\n' ' ' <"$scan_err")). Re-detecting..."
            FAILED_DEVICES+=("${SCAN_DEVICE}")
            SCAN_DEVICE=""
            SELECTED_SOURCE=""
            rm -f "$scan_err"
            sleep 2
            continue
        fi
    fi
    if [[ -s "$scan_err" ]]; then
        # ADF empty / document-feeder out of documents is expected between loads.
        grep -viE 'rounded value of br-' "$scan_err" || true
    fi
    rm -f "$scan_err"

    new_count=$(count_pages)
    scanned_this_batch=$((new_count - old_count))

    if [[ "$scanned_this_batch" -gt 0 ]]; then
        echo "   Scanned ${scanned_this_batch} page(s)"
        last_successful_scan=$(date +%s)
    else
        echo "   ADF appears empty."
    fi

    current_time=$(date +%s)
    if [[ -n "$last_successful_scan" ]] &&
        [[ $((current_time - last_successful_scan)) -ge $MULTI_LOAD_TIMEOUT ]]; then
        echo "   Timeout reached. Proceeding..."
        break
    fi
    sleep 5
done

# -------------------------- Processing --------------------------
shopt -s nullglob
mapfile -t pages < <(printf '%s\n' page_*."${SCAN_FORMAT}" | sort -V)
shopt -u nullglob

if [[ ${#pages[@]} -eq 0 ]]; then
    echo "ERROR: No pages scanned (ADF stayed empty). Not calling img2pdf."
    cd ..
    rm -rf "$WORK_DIR" 2>/dev/null || true
    exit 1
fi

processed=()
for img in "${pages[@]}"; do
    if convert "$img" -shave "${MARGIN_TO_SHAVE}x${MARGIN_TO_SHAVE}" -virtual-pixel White \
        -blur "0x${BLUR_RADIUS}" -fuzz "${FUZZ_PERCENT}" -trim -format "%wx%h" info: 2>/dev/null |
        awk -F'x' -v minw="${MIN_CONTENT_WIDTH}" -v minh="${MIN_CONTENT_HEIGHT}" \
            '{if($1<minw || $2<minh) exit 0; else exit 1}'; then
        echo "→ Removing blank page: $img"
        rm -f "$img"
        continue
    fi
    processed+=("$img")
done

if [[ ${#processed[@]} -eq 0 ]]; then
    echo "ERROR: All pages looked blank. Not calling img2pdf."
    cd ..
    rm -rf "$WORK_DIR" 2>/dev/null || true
    exit 1
fi

img2pdf "${processed[@]}" -o intermediate.pdf
ocrmypdf --language eng --rotate-pages --rotate-pages-threshold "${OCR_ROTATE_THRESHOLD}" \
    --deskew --clean --optimize 1 --force-ocr intermediate.pdf "temp_ocr.pdf"

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
