---
name: rperks-activate-coupons
description: Own-account RPerks / Ridley's coupon activator (puppeteer-core, user systemd timer). Use when RPerks, shopridleys, coupon timer, or leftover Activate buttons come up.
---

# RPerks Activate Coupons

Local puppeteer-core runner for **your own** RPerks account. Vendor-locked to
`https://rperks.shopridleys.com` (cashback iframe `https://prod.kacu.app`).
Credentials stay in `config.json` (mode 600) or `RPERKS_USERNAME` /
`RPERKS_PASSWORD`. Never copy the password into memory, chat, or the pack.

## Layout

| Path | Role |
|------|------|
| `~/.local/bin/rperks-activate` | PATH wrapper → `run-rperks.mjs` |
| `~/.local/bin/rperks-activate-coupons/` | App (`run-rperks.mjs`, `config.example.json`) |
| `~/.config/rperks-chrome` | Dedicated Chromium profile |
| `~/.config/systemd/user/rperks-activate.{service,timer}` | Oneshot + twice-daily timer |
| `~/.config/systemd/user/rperks-activate-install.service` | `npm install --omit=dev` |

Pack sources: `bin/rperks-activate-coupons/`, `share/rperks-activate-coupons/`.
`install.sh --bin` copies them and daemon-reloads. It does not enable the timer.

## Walk order

1. `/pages/personal-ad`
2. `/pages/collections/collection/DigitalOffers`
3. `/pages/collections/collection/MoreCoupons`
4. `/pages/cashback` (`#KacuIframe`)

Skip ADDED, ACTIVATED, ADD TO LIST. `leftover=N` means N Activate buttons were
still on the page after the click pass.

## Commands

```bash
rperks-activate
rperks-activate --dry-run
rperks-activate --headless=false
rperks-activate --fresh
systemctl --user start rperks-activate.service
journalctl --user -u rperks-activate.service -e
```

`--fresh` clears cookies/cache/storage for rperks.shopridleys.com, prod.kacu.app,
and ridleys.immapi.com, then logs in. The account menu has no reliable Sign Out.

Timer: `OnCalendar=*-*-* 0/12:02:04`, Persistent, 10min jitter.

Headless `/login` can bounce to `/` or `/welcome` with no inputs. The runner
clicks Sign In once more, then opens `/login` again (up to 3 attempts). Watch
with `--headless=false` on Wayland (`--ozone-platform=wayland`).

## Anti-patterns

- Committing `config.json`, `node_modules`, or the Chrome profile
- `pkill -f` a pattern that also matches the shell wrapper cmdline
- Reinstalling from an old tree whose timer is still Tue/Fri 07:00
- Packing a real store geopin; example config uses `null` latitude/longitude
