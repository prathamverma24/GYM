# AthleteOS Architecture

```text
Browser / installable PWA
  ├─ Next.js App Router and Concept 3 component system
  ├─ TanStack Query server cache
  ├─ local workout draft/outbox
  └─ lazy browser-side MediaPipe adapter
                 │ REST /api/v1 + HTTP-only session
FastAPI modular monolith
  ├─ identity + consent
  ├─ athlete profile + metrics + readiness
  ├─ training + sessions + progression
  ├─ nutrition + food search + water
  ├─ habits + schedule-aware streaks
  ├─ dashboard + reports
  └─ CV assessment + recommendation records
                 │
PostgreSQL (durable system of record)
Redis (cache, rate limit, future jobs)
Private S3-compatible storage (optional raw media, disabled by default)
```

Timestamps are stored in UTC. Domain operations that use a calendar date take an explicit athlete-local ISO date. Canonical measurements are kilograms, centimetres and millilitres; display conversion is a presentation concern.

