# IaC Plan Analysis

Prefer structured plan output:

```bash
tofu plan -out=tfplan && tofu show -json tfplan
```

## Risk buckets
- **Critical:** destroy/replace, security groups, IAM, encryption
- **High:** in-place changes on production, network, DNS
- **Medium:** tags, scaling, non-critical config
- **Low:** outputs, locals, comments

## Always check
- Resources destroyed or replaced
- Open ingress (`0.0.0.0/0`) on sensitive ports
- IAM least privilege
- State drift vs intent
- Cascading destroys
- `count` / `for_each` index shifts

## Report shape
```
## Plan Summary
- N add, M change, D destroy

## Critical Changes
- …

## Recommendations
- …
```
