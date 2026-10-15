---
name: server-package-install-dating
description: "Server companion to software-install-dating. Extend core install-date logic to rpm, dpkg, Windows Installer, container images, and package history for patch compliance and build validation."
type: knowledge
lifecycle: active
---

# Server Package Install Dating

Thin companion to `software-install-dating`.

## Core reuse

Follow `software-install-dating` for the principle of earliest artifact + version evidence and the `INSTALL_DATING` block.

## Server artifacts

- RPM: `rpm -qi <pkg>` (Install Date), `/var/log/dnf.log`, `yum history`
- Debian: `/var/log/dpkg.log`, `/var/log/apt/history.log`
- Windows: SetupAPI, Windows Installer logs, Uninstall registry keys
- Containers: image created timestamp, layer history (`docker history`, `podman`)
- Golden image / cloud-init / ignition timestamps

## Output

Same `INSTALL_DATING` block; add `package_manager: rpm|dpkg|msi|container|other`.

## Upstream note

Claimed-vs-actual comparison logic is shared.
