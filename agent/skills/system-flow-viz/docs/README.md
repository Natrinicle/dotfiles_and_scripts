# Preview assets

Baked sample of a compose-stack **data flow path** dashboard. HTTPS is
`volume: high` (fast dense drops), SQL is `medium`, the job queue is `low`
(slow sparse drops).

| File | What |
|------|------|
| `compose-stack.html` | Live CSS dashboard (open in a real browser) |
| `compose-stack.gif` | 16-frame loop for READMEs and chat |
| `compose-stack.png` | Mid-loop still |

Rebuild from `examples/compose-stack.json`:

```bash
python3 ../scripts/render_flow.py html ../examples/compose-stack.json -o compose-stack.html
python3 ../scripts/render_flow.py bake ../examples/compose-stack.json -o compose-stack.gif
```
