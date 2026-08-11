# Requirements Traceability

Source precedence: Technical Requirements Document (TRD) → Product Requirements Document (PRD) → Concept 3 UI handoff → Implementation Plan.

| Source requirement | Planned realization | Verification |
| --- | --- | --- |
| TRD ENG-01, §7 | SQLAlchemy/PostgreSQL durable domain entities; Redis/cache is optional | Migration and API integration tests |
| TRD ENG-02, §10 | Immutable `RecommendationDecision` with evidence, rule version, confidence and explanation | Rules unit tests and response assertions |
| TRD ENG-03/04, §11/15 | Browser-side scan, derived features by default, explicit confidence and safe copy | CV quality tests; UI copy review |
| TRD ENG-05, §4.3/16 | Client operation UUIDs and unique set/water/habit writes | Duplicate-retry API tests |
| TRD ENG-06/07 | Typed tracking schemas and versioned program/rule/data records | Schema and fixture tests |
| TRD ENG-08, NFR-003 | Persisted Zustand workout draft/outbox, optimistic inputs and sync state | Refresh/offline component tests |
| TRD IAM-001..008 | Password hashing, opaque server sessions in HTTP-only cookie, ownership dependencies, consent records | Authentication and BOLA API tests |
| TRD §8/14 | Internal food system of record, normalized names/aliases, ranking and nutrient snapshots | Golden-query and nutrient-history tests |
| TRD §9 | Deterministic program builder, modality-aware sets, double progression | Personalization matrix tests |
| TRD §12 | Schedule-aware local-date habit completions and month matrix | Timezone/schedule streak unit tests |
| TRD §13/16 | Aggregated dashboard, weekly and monthly series | Reconciliation tests |
| PRD §3/4 | Resumable onboarding and daily action dashboard | E2E flow |
| PRD §6 | Indian-first aliases and household serving options | Golden food search corpus |
| PRD §7 | Day view, live logger, prior performance, PR/progression | Workout E2E and calculation tests |
| PRD §12 | Export/delete/consent boundaries and no sensitive logs | API tests and security review |
| Concept 3 pages 2-20 | CSS tokens, 14-18px cards, Poppins, gradient CTA, dark surfaces, responsive navigation | Visual/browser verification |
| Implementation Plan §16-23 | Unit/API/frontend/E2E gates, containers, logs, health and docs | CI workflow |

## Safety assertions

- No endpoint infers body type, medical posture diagnoses, injury diagnoses, or photo-derived body-fat percentage.
- Equipment and pain/limitation constraints are authoritative in plan generation.
- CV-derived evidence is optional and lower priority than performance, adherence and recovery.
- Historical body metrics and meal nutrient snapshots are append-only.
- Raw photos are not accepted or retained by the initial API.

