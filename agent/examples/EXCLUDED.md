# Not packaged

Items left on the host or in other repos. Do not dump these into this
general pack.

| Item | Reason |
|------|--------|
| Host-only k8s/ops skills (CNI, PVC, Helm, gateway, Tailscale, Vault, …) | Cell/homelab runbooks, not a shareable agent pack |
| `court-case-monitor` | Specialized pack (`court-case-monitor-toolkit`) |
| `deploy-creator-bootcamp` | Product deploy playbook |
| Live `adversarial-analysis` / `communication-pattern-analysis` bodies | Pack ships short stubs; live files stay under `{AGENT_HOME}/skills/` |
| Live writing-style corpus | Pack ships `{user}` placeholders under `nate-writing-style`; host corpus stays on the host |
| `.find-patch-queue.json` / `.lock` | Session queue; gitignored |
| Host-app-only skill packs | Prefer project-local skills |
| Large office document skill bundles | Huge schema trees |
| Live tokens, MCP OAuth, private hosts | Secrets |
| Personal contact memory dumps | PII |
| RPerks `config.json`, Chrome profile, `node_modules/` | Host secrets / re-downloadable |
| Firecrawl / other host-only skills | Not this pack |
