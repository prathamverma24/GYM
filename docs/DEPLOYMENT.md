# Deployment

The web and API build independently. The provided Compose profile runs PostgreSQL, Redis, API and web. Production should use managed PostgreSQL with point-in-time recovery, managed Redis, private S3-compatible storage, TLS at the edge, secret-manager injection and separate migration credentials.

Before production: replace all secrets, enable secure cookies, set an exact CORS allowlist, run migrations as a distinct job, verify backup restore, configure telemetry/alerts and complete the authorization/upload abuse test matrix.

## Vercel

Set the Vercel project's Root Directory to `apps/web`. The project contains a Python function at `api/index.py`, so browser requests use the same-origin `/api/v1` path and do not depend on `localhost` or cross-site cookies.

Attach managed Postgres and expose its connection string as `DATABASE_URL` or `POSTGRES_URL`. Without it, previews fall back to SQLite in `/tmp`; that fallback is intentionally ephemeral and is not suitable for user accounts or production data. Set a unique `SESSION_SECRET`, keep `SESSION_COOKIE_SECURE=true`, and leave `NEXT_PUBLIC_API_URL` unset unless the API is intentionally deployed on a separate HTTPS domain.
