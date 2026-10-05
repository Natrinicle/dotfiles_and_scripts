# RPerks Activate Coupons

Own-account runner that clicks **Activate** on Ridley's RPerks digital offers.

Vendor-specific: origin `https://rperks.shopridleys.com` and cashback iframe
`https://prod.kacu.app`. Replace those URLs only if you use another chain's
portal.

Walk order:

- `/pages/personal-ad`
- `/pages/collections/collection/DigitalOffers`
- `/pages/collections/collection/MoreCoupons`
- `/pages/cashback` (`#KacuIframe`)

Skips buttons labeled ADDED, ACTIVATED, and ADD TO LIST. `leftover` in the log
is how many Activate buttons were still visible after the click pass.

## Install (from this toolkit)

```bash
./install.sh --bin --agent
cp ~/.local/bin/rperks-activate-coupons/config.example.json \
   ~/.local/bin/rperks-activate-coupons/config.json
chmod 600 ~/.local/bin/rperks-activate-coupons/config.json
# fill username/password and your store latitude/longitude
systemctl --user enable --now rperks-activate-install.service
systemctl --user enable --now rperks-activate.timer
```

`install.sh --bin` copies the app and user units. It does **not** enable the
timer. `rperks-activate-install.service` runs `npm install --omit=dev` in the
app directory.

Credentials: `RPERKS_USERNAME` / `RPERKS_PASSWORD`, or `config.json` (mode 600,
gitignored). Never commit `config.json`. Never paste the password into chat.

Dedicated Chrome profile: `~/.config/rperks-chrome`. Chromium binary:
`/usr/bin/chromium` (or `CHROME_PATH`).

## Commands

```bash
rperks-activate                 # uses config.json / env
rperks-activate --dry-run
rperks-activate --headless=false
rperks-activate --fresh         # wipe rperks/kacu/immapi session, then log in
systemctl --user start rperks-activate.service
journalctl --user -u rperks-activate.service -e
```

`--headless=false` overrides `config.json`. On Wayland the runner adds
`--ozone-platform=wayland`. Headed failure holds the window 8 minutes and
writes `/tmp/rperks-watch.png`. Success leaves the window open 20s.

## Timer

`share/rperks-activate-coupons/rperks-activate.timer`:

- `OnCalendar=*-*-* 0/12:02:04` (about 00:02 and 12:02 local)
- `Persistent=true`
- `RandomizedDelaySec=10min`

Headless `/login` sometimes bounces to `/` with no fields. The runner retries
Sign In once per attempt (up to 3). Saved profile usually skips login.

## Other entry points

| File | Use |
|------|-----|
| `run-rperks.mjs` | Unattended login + all pages (systemd uses this) |
| `activate-rperks-cdp.mjs` | Attach to an already-running Chrome via CDP |
| `devtools-snippet.js` | Paste in DevTools on an RPerks page |
| `rperks-activate.user.js` | Tampermonkey; also matches `prod.kacu.app` |

Cashback Activate buttons live in the cross-origin `#KacuIframe`. A parent-page
snippet cannot click them.
