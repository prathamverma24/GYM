# API Conventions

- Base path: `/api/v1`
- JSON dates use ISO `YYYY-MM-DD`; timestamps are UTC ISO-8601.
- Authentication uses the `athleteos_session` HTTP-only cookie.
- Athlete-owned reads and writes resolve the current user server-side; client-provided owner IDs are ignored or rejected.
- Retry-prone mutations accept `Idempotency-Key` or a client operation UUID.
- Errors use `{ "code", "message", "details", "request_id", "retryable" }`.
- OpenAPI is available from `/docs` in local/development environments.

The generated schema is the contract source for a future generated TypeScript client. The current handwritten client is typed and isolated in `apps/web/lib/api.ts`.

## Program editing

- `GET /programs/templates` lists all dataset workout structures and marks profile-compatible recommendations.
- `POST /programs/templates/{split_id}/activate` switches the athlete to a selected dataset plan.
- `POST`, `PATCH`, and `DELETE /programs/{program_id}/days...` manage workout days and their prescribed exercises.
- Every plan edit uses copy-on-write versioning. The prior plan is superseded instead of modified, so workout sessions and set history continue to reference the exact prescription that was performed.
