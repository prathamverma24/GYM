# Deployment

The web and API build independently. The provided Compose profile runs PostgreSQL, Redis, API and web. Production should use managed PostgreSQL with point-in-time recovery, managed Redis, private S3-compatible storage, TLS at the edge, secret-manager injection and separate migration credentials.

Before production: replace all secrets, enable secure cookies, set an exact CORS allowlist, run migrations as a distinct job, verify backup restore, configure telemetry/alerts and complete the authorization/upload abuse test matrix.

## Vercel

Set the Vercel project's Root Directory to `apps/web`. The project contains a Python function at `api/index.py`; `vercel.json` forwards the `/api/v1` route tree to that function. Browser requests therefore use the same-origin `/api/v1` path and do not depend on `localhost` or cross-site cookies.

The deployable backend wheel is stored in `apps/web/vendor`. Vercel's Python builder installs the immutable GitHub copy referenced by `apps/web/requirements.txt`, avoiding incorrect double-resolution of local requirement paths. After backend changes, rebuild the wheel, commit it, and update that URL to the commit containing the new wheel:

```powershell
python -m pip wheel .\apps\api --no-deps --wheel-dir .\apps\web\vendor
```

Attach Turso by setting `TURSO_DATABASE_URL` and the secret `TURSO_AUTH_TOKEN`, or attach managed Postgres and expose its connection string as `DATABASE_URL` or `POSTGRES_URL`. Turso takes precedence when both are present. Without either database, previews fall back to SQLite in `/tmp`; that fallback is intentionally ephemeral and is not suitable for user accounts or production data. Set a unique `SESSION_SECRET`, keep `SESSION_COOKIE_SECURE=true`, and leave `NEXT_PUBLIC_API_URL` unset unless the API is intentionally deployed on a separate HTTPS domain.

The Vercel Python function is pinned to Python 3.12 in `apps/web/.python-version` because the libSQL driver ships a compatible prebuilt Linux wheel for that runtime.

For a new Turso database, create the schema once and seed the reference catalogues with `python scripts/seed_turso.py` while `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` are set. The script refuses to modify a partially populated catalogue. After initialization, set `AUTO_CREATE_DB=false` in Vercel so cold starts do not perform schema introspection.
