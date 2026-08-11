# Deployment

The web and API build independently. The provided Compose profile runs PostgreSQL, Redis, API and web. Production should use managed PostgreSQL with point-in-time recovery, managed Redis, private S3-compatible storage, TLS at the edge, secret-manager injection and separate migration credentials.

Before production: replace all secrets, enable secure cookies, set an exact CORS allowlist, run migrations as a distinct job, verify backup restore, configure telemetry/alerts and complete the authorization/upload abuse test matrix.

