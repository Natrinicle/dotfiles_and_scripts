---
name: leftover-account-sessions
description: >
  Use when leftover signed-in devices, forgotten Google/Apple/TV sessions,
  third-party keyboards with Full Access, Always location, full Photos/media
  access, stale apps still phoning home, App Privacy Report, Photos ambient
  on a TV, KDE Connect trusted devices, or similar privacy-audit posts.
  Also ADB session/permission audits. Overlay XPL-EX / XPrivacyLua when present.
---

# Leftover account sessions

Own device / own account only. Read-only until the user names a revoke,
uninstall, or sign-out.

Viral posts in this class are forgotten **sessions and grants**, not a
new exploit. Map the claim onto this checklist. Do not treat OS
`appops allow` as data leaving the device when XPL-EX is restricting the
matching Java hook.

## Layers (run in this order)

1. **Cloud sessions** — Google device-activity, Photos-on-TV / ambient,
   Cast / Home, Apple ID devices if an Apple account exists. Agent
   Chromium is often signed out; use the user's daily browser, do not
   type passwords.
2. **IME / accessibility / notification listeners** — these bypass
   Location appops. A third-party IME sees keystrokes. A notification
   listener sees 2FA codes.
3. **OS grants** — `cmd appops query-op … allow` for location, media,
   camera, mic. `ACCESS_BACKGROUND_LOCATION` granted is the Always
   analogue.
4. **XPL-EX overlay** (when `eu.faircode.xlua` is installed) — live
   `xlua.db` `assignments.restricted=1`. IDs / ads / file-list hooks
   often block what appops still shows as allow. XPL-EX does **not**
   cover IMEs, notification listeners, accessibility, native code, or
   apps outside LSPosed scope.
5. **Paired companions** — KDE Connect `trusted_devices`, watches,
   Cast. Old phones still trusted are the same class as a leftover TV.

## ADB dump

```bash
{AGENT_HOME}/skills/leftover-account-sessions/scripts/adb-leftover-sessions.sh
```

Needs USB debugging. If `adb devices` is empty but `lsusb` shows an ADB
interface, `adb kill-server && adb start-server`. Magisk Shell: `su -c
id`; if `Permission denied` with no prompt, Superuser already Denied —
Allow **Shell** in Magisk, then retry. Use `su -mm` + `cat` for
`/data/misc/xplex-*/xlua.db` (toybox `cp` is denied).

## Flag

| Surface | Flag when |
|---------|-----------|
| IME | Third-party enabled; extra flag if package has `INTERNET` |
| Keyboard leftover | Gboard / OEM IME installed with media/location allow while not the current IME |
| Always location | `ACCESS_BACKGROUND_LOCATION` granted, or `MONITOR_HIGH_POWER_LOCATION` allow on a third-party package |
| Photos | `READ_MEDIA_IMAGES` allow on a package that is not a gallery/camera/messenger the user still uses |
| Stale | Third-party lastTimeUsed older than 6 months **and** still has dangerous grants or listeners |
| Cloud / pair | Device the user no longer has, still signed in or trusted |
| QR / font keyboard | Scanner or IME unused for months, camera or full-input still granted |

Do not dump account emails, KDE Connect `privateKey`, or XPL-EX
`settings` values (IMEI / android_id spoof material). Names of trusted
devices and package names are enough.

IME `lastTimeUsed` in usagestats often misses keystrokes. Treat an
enabled IME as live.

## Fixes (order)

1. Cloud: sign out leftover TVs / tablets / old phones; rotate password
   if a device the user no longer holds was still active.
2. Disable extra IMEs; keep one keyboard.
3. Drop unused notification listeners and accessibility services.
4. Unpair leftover KDE Connect / watch / Cast targets.
5. Revoke Always location and full media on apps that do not need them.
6. Uninstall stale scanners / one-shot apps.

XPL-EX stays the ID/ad/file overlay; it does not replace steps 1–4.

## Palace

Entity `leftover-account-sessions`. Unique phrase:
`leftover account sessions IME appops XPL-EX xlua.db KDE Connect trusted devices Photos ambient 2026-10-29`.
File methods the same turn they are recovered.
