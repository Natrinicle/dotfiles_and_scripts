# OpenTelemetry Instrumentation

Apply when adding or reviewing tracing, metrics, or log correlation.

## Span naming
- Use low-cardinality names: `component.operation` (e.g. `db.query`, `http.request`).
- Never put IDs, emails, or raw URLs in span names; use attributes instead.

## Span lifecycle
- End spans in `finally` (or equivalent) so errors still close them.
- On failure: record the exception, set error status, then end.
- Prefer APIs that attach the span to active context automatically.
- Do not call `.end()` on a span you did not start (e.g. the framework HTTP span).

## Response-end hazards
- Handlers that fire after the response is finished often run *after* the framework has already ended the HTTP span. Attribute writes there are silent no-ops.
- Prefer framework hooks that run **before** the span ends (e.g. custom attribute callbacks on the HTTP instrumentation).

## Metrics
- Labels must stay low-cardinality (service, env, operation type).
- Never use user IDs, emails, or request-specific values as metric labels.
- Guard observable callbacks so disabled instrumentations stop reporting.

## PII in telemetry
Never export:
- Emails, phones, passwords, tokens, API keys
- Full legal names, government IDs, account numbers
- Raw request/response bodies with user content
- Full URLs with query strings (may carry tokens or filters)

Prefer:
- Opaque user ids only when required, documented as pseudonymous
- Route templates (`/users/:id`) instead of concrete paths
- Error codes/messages without interpolated user input

## Dependencies
- Prefer official OpenTelemetry instrumentations for the stack.
- Extend for gaps; do not reimplement what upstream already covers.
- Check upstream changelogs before writing custom instrumentation.
