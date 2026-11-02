#!/usr/bin/env bash
# Read-only leftover-session dump: IMEs, listeners, appops, XPL-EX overlay.
# Own device. Does not print account emails, KDE private keys, or xlua setting values.
set -euo pipefail

usage() {
	echo "Usage: adb-leftover-sessions.sh [-s serial] [-o outdir]" >&2
	exit 2
}

SERIAL=""
OUTDIR=""
while getopts "s:o:h" opt; do
	case "$opt" in
	s) SERIAL=$OPTARG ;;
	o) OUTDIR=$OPTARG ;;
	*) usage ;;
	esac
done

ADB=(adb)
if [[ -n $SERIAL ]]; then
	ADB+=(-s "$SERIAL")
fi

if ! "${ADB[@]}" get-state >/dev/null 2>&1; then
	echo "No ADB device. Enable USB debugging and authorize this computer." >&2
	"${ADB[@]}" devices -l >&2 || true
	exit 1
fi

if [[ -z $OUTDIR ]]; then
	OUTDIR="/tmp/leftover-sessions-$(date -u +%Y%m%dT%H%M%SZ)"
fi
mkdir -p "$OUTDIR"
chmod 700 "$OUTDIR"

redact() {
	sed -E 's/[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}/{account}/g'
}

adb_sh() {
	"${ADB[@]}" shell "$@"
}

su_sh() {
	"${ADB[@]}" shell su -mm -c "$1"
}

have_su=0
if su_sh 'id' 2>/dev/null | grep -q 'uid=0'; then
	have_su=1
fi

{
	echo "serial=$("${ADB[@]}" get-serialno)"
	adb_sh getprop ro.product.model
	adb_sh getprop ro.build.display.id
	adb_sh getprop ro.build.version.release
	adb_sh date
	echo "su=$have_su"
} >"$OUTDIR/device.txt"

adb_sh ime list -s >"$OUTDIR/ime-short.txt"
adb_sh settings get secure default_input_method >"$OUTDIR/ime-default.txt"
adb_sh settings get secure enabled_input_methods >"$OUTDIR/ime-enabled.txt"
adb_sh settings get secure enabled_accessibility_services >"$OUTDIR/a11y.txt"
adb_sh settings get secure enabled_notification_listeners >"$OUTDIR/notif-listeners.txt"

for op in FINE_LOCATION COARSE_LOCATION MONITOR_LOCATION MONITOR_HIGH_POWER_LOCATION \
	READ_MEDIA_IMAGES READ_MEDIA_VIDEO CAMERA RECORD_AUDIO; do
	adb_sh cmd appops query-op "$op" allow >"$OUTDIR/appops-${op}-allow.txt" 2>&1 || true
done

adb_sh dumpsys account 2>/dev/null | redact >"$OUTDIR/account-redacted.txt" || true
adb_sh pm list packages -3 >"$OUTDIR/packages-third.txt"

if [[ $have_su -eq 1 ]]; then
	xpl=$(su_sh 'find /data/misc -maxdepth 2 -name xlua.db 2>/dev/null | head -1' | tr -d '\r')
	if [[ -n $xpl ]]; then
		"${ADB[@]}" exec-out su -mm -c "cat $xpl" >"$OUTDIR/xlua.db"
		if command -v sqlite3 >/dev/null; then
			sqlite3 "$OUTDIR/xlua.db" \
				"SELECT category, COUNT(*) FROM assignments WHERE restricted=1 GROUP BY category ORDER BY 2 DESC;" \
				>"$OUTDIR/xlua-restricted-packages.txt"
			sqlite3 "$OUTDIR/xlua.db" \
				"SELECT CASE WHEN instr(hook,'.')>0 THEN substr(hook,1,instr(hook,'.')-1) ELSE hook END, COUNT(*) FROM assignments WHERE restricted=1 GROUP BY 1 ORDER BY 2 DESC;" \
				>"$OUTDIR/xlua-restricted-prefixes.txt"
		fi
	fi
	# KDE Connect trusted device names only (no keys)
	if su_sh 'test -f /data/user/0/org.kde.kdeconnect_tp/shared_prefs/trusted_devices.xml' >/dev/null 2>&1; then
		"${ADB[@]}" exec-out su -mm -c \
			'grep -h deviceName /data/user/0/org.kde.kdeconnect_tp/shared_prefs/*.xml' \
			>"$OUTDIR/kde-device-names.txt" 2>/dev/null || true
	fi
fi

{
	echo "OUTDIR=$OUTDIR"
	echo "default_ime=$(tr -d '\r' <"$OUTDIR/ime-default.txt")"
	echo "enabled_ime=$(tr -d '\r' <"$OUTDIR/ime-enabled.txt")"
	echo "a11y=$(tr -d '\r' <"$OUTDIR/a11y.txt")"
	echo "notif_listeners=$(tr -d '\r' <"$OUTDIR/notif-listeners.txt")"
	echo "su=$have_su"
	if [[ -f $OUTDIR/xlua-restricted-packages.txt ]]; then
		echo "xlua_restricted_packages:"
		cat "$OUTDIR/xlua-restricted-packages.txt"
	fi
	if [[ -f $OUTDIR/kde-device-names.txt ]]; then
		echo "kde_device_names:"
		cat "$OUTDIR/kde-device-names.txt"
	fi
} | tee "$OUTDIR/summary.txt"
