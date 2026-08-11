# Architecture Decisions

## ADR-001 — Modular monolith

Status: accepted

AthleteOS uses a Next.js web application and one FastAPI deployable with explicit identity, athlete, training, nutrition, habits, analytics, recommendations and CV domain packages. This follows the TRD and keeps transactions and ownership checks straightforward while preserving separable boundaries.

## ADR-002 — Server-managed opaque sessions

Status: accepted

The web client authenticates with an opaque random session token in a Secure/HTTP-only/SameSite cookie. Only a SHA-256 digest is stored server-side. Passwords use versioned PBKDF2-HMAC-SHA256 with per-password random salt and a high work factor. Long-lived bearer tokens are never stored in browser storage.

## ADR-003 — PostgreSQL production, SQLite developer fallback

Status: accepted

PostgreSQL is the production source of truth. SQLite is supported solely for zero-dependency local evaluation and isolated tests because Docker is not installed in the current workspace. Models avoid SQLite-only behavior and CI/container profiles exercise PostgreSQL.

## ADR-004 — Snapshot mutable reference data in logs

Status: accepted

Meal items snapshot calories/macros/source at logging time. Programs snapshot prescriptions. Corrections to catalogue data never rewrite athlete history.

## ADR-005 — Browser-first, derived-only CV

Status: accepted

The web app lazy-loads MediaPipe only inside the body-scan flow, applies quality gates, calculates versioned normalized ratios and sends only derived features. The API intentionally has no raw-photo upload in the initial MVP. Private object storage can be introduced behind separate consent.

## ADR-006 — Deterministic personalization

Status: accepted

Plan generation and progression are versioned rules, not generative output. Inputs, reason codes and evidence are stored. Changes become proposals at a planning boundary and never rewrite completed history.

## ADR-007 — Local workout outbox

Status: accepted

Active workout state and client operation UUIDs are stored locally after each input. The API accepts idempotent set writes. On reconnect, the client retries pending operations and shows synchronization state.

## ADR-008 — CSS tokens with utility tooling

Status: accepted

Tailwind is available for layout utilities, while semantic CSS variables and small reusable primitives own the Concept 3 visual system. This keeps domain UI readable and avoids hard-coded color drift.

