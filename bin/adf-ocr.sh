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
# File-and-route (adf-ocr-file.py): taxonomy, destination root, classify model.
# ADF_OCR_TAXONOMY="${ADF_OCR_TAXONOMY:-$HOME/.config/adf-ocr/taxonomy.yaml}"
# ADF_OCR_OUT_ROOT="${ADF_OCR_OUT_ROOT:-$HOME/Documents}"
# ADF_OCR_CLASSIFY_MODEL="${ADF_OCR_CLASSIFY_MODEL:-gemma4:12b}"
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

CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/adf-ocr"
mkdir -p "$CACHE_ROOT"
WORK_DIR="${CACHE_ROOT}/scan_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

FILE_PY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/adf-ocr-file.py"
if [[ ! -f "$FILE_PY" ]]; then
	FILE_PY="$(command -v adf-ocr-file.py || true)"
fi

if command -v curl >/dev/null 2>&1; then
	echo "=== Preloading ${LLM_MODEL} LLM ==="
	curl -s -X POST "$LLM_SERVER_URL" -H "Content-Type: application/json" -d '{"model": "'"$LLM_MODEL"'"}' >/dev/null 2>&1
fi

echo "=== Starting continuous ADF scan ==="

last_successful_scan=""
scan_started=$(date +%s)

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
	if [[ -z "$last_successful_scan" ]] &&
		[[ $((current_time - scan_started)) -ge $MULTI_LOAD_TIMEOUT ]]; then
		echo "   No pages after ${MULTI_LOAD_TIMEOUT}s. ADF stayed empty."
		break
	fi
	sleep 5
done

# -------------------------- File and route --------------------------
shopt -s nullglob
mapfile -t pages < <(printf '%s\n' page_*."${SCAN_FORMAT}" | sort -V)
shopt -u nullglob

if [[ ${#pages[@]} -eq 0 ]]; then
	echo "ERROR: No pages scanned (ADF stayed empty)."
	cd /
	rm -rf "$WORK_DIR" 2>/dev/null || true
	exit 1
fi

if [[ ! -f "${FILE_PY}" ]]; then
	echo "ERROR: adf-ocr-file.py not found next to adf-ocr.sh (install both to ~/.local/bin)."
	exit 1
fi

echo "=== OCR, classify, and file ==="
export MARGIN_TO_SHAVE BLUR_RADIUS FUZZ_PERCENT MIN_CONTENT_WIDTH MIN_CONTENT_HEIGHT
export OCR_ROTATE_THRESHOLD LLM_SERVER_URL LLM_MODEL LLM_TEMPERATURE LLM_MAX_TOKENS
export SCAN_FORMAT SCAN_DUPLEX
file_args=(python3 "$FILE_PY" --pages-dir "$WORK_DIR")
if [[ "${SELECTED_SOURCE}" == "ADF Duplex" ]]; then
	file_args+=(--duplex)
else
	file_args+=(--no-duplex)
fi
if [[ -n "${ADF_OCR_TAXONOMY:-}" ]]; then
	file_args+=(--taxonomy "$ADF_OCR_TAXONOMY")
fi
if [[ -n "${ADF_OCR_OUT_ROOT:-}" ]]; then
	file_args+=(--out-root "$ADF_OCR_OUT_ROOT")
fi
if [[ -n "${ADF_OCR_CLASSIFY_MODEL:-}" ]]; then
	file_args+=(--classify-model "$ADF_OCR_CLASSIFY_MODEL")
fi
case "${ADF_OCR_NO_LLM:-}" in
1 | true | yes | on) file_args+=(--no-llm) ;;
esac
if ! "${file_args[@]}"; then
	echo "ERROR: file-and-route failed. Pages kept in $WORK_DIR"
	exit 1
fi

if [[ -f "$WORK_DIR/.keep" ]]; then
	echo "=== Keeping scan cache (review or --keep-cache) ==="
	echo "   $WORK_DIR"
else
	echo "=== Cleaning up scan cache ==="
	cd /
	rm -rf "$WORK_DIR" 2>/dev/null || true
fi

echo "======================================================================"
echo "DONE"
echo "   Cache removed: $WORK_DIR"
echo "======================================================================"
