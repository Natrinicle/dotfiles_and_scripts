---
name: detect-pii-leaks
description: >
  Find PII escaping into logs, traces, errors, URLs, or client storage when reviewing
  code that handles user or auth data. Also when examples, self-tests, docs, or OCR/mail
  fixtures may contain real personal, company, account, or mail identifiers.
---

# Detect PII Leaks

Two phases: **pattern scan** (cheap) then **risk judgment** (stronger model if unsure).

## Where leaks show up

1. **Logs** — `console.log`, structured loggers dumping `req.body`, user objects, tokens  
2. **Traces** — span attributes with emails, raw URLs, payloads; custom tags on business events  
3. **Errors** — messages that interpolate user input or serialize full error causes with bodies  
4. **URLs** — query strings with emails, tokens, filter expressions; client routers sharing state  
5. **Browser storage** — localStorage/sessionStorage holding profile dumps instead of opaque session ids  
6. **Fixtures / self-tests / docs** — sample OCR text, mailers, account numbers, barcodes, or
   "anonymized" copies of real statements that still identify a person, employer, bank/HSA,
   credit union, or mail piece

## Heuristics

Search for field names and usage: email, phone, password, token, ssn, accountNumber, etc.
Then ask: does this value leave the trust boundary?

**Usually OK:** opaque ids, route templates (`/users/:id`), redacted hashes, enums,
obvious fictional placeholders, all-same-digit sample accounts, demo IMB prefixes
(`9ZZ` / `9SYN` / `9TEST` / `9DEMO` / `9SAMPLE` / `9FAKE`), public vendor/API names.  
**Usually bad:** full request bodies, `JSON.stringify(user)`, `http.url` with query string,
error strings with `${email}`, real account/member numbers, real mail barcodes, real
person/company names in examples — including reversible masks of those values.

For shareable packs, invent fixtures **from scratch**. Prefer `package-toolkit`
residual + identity-subagent scans (code included by default) over hoping a mask is enough.
Do not embed original denylist strings in tracked tests or docs.

## HTTP instrumentation gotcha

Auto-instrumentation often sets `http.url` / `http.target` from the raw URL including
query. Prefer setting attributes from the **matched route template** and strip queries.

## Output

List findings with file:line, why it’s risky, and a concrete safer pattern. Prefer
fixing code you wrote; propose patches for pre-existing issues.
