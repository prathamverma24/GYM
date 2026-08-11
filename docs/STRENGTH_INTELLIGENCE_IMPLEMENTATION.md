# AthleteOS Strength Intelligence

## Audited data flow

The workout logger persists one `WorkoutSession` per performed training day and one `SetLog` per prescribed exercise set. A set can record external load, repetitions, hold time, distance, assistance, RIR, RPE and completion state. `PrescribedExercise` links the set to `Exercise`, whose dataset-backed record already contains modality, tracking metric, movement pattern, primary muscles and secondary muscles. Progress currently reads calendar reports from `app.api.analytics` and body metrics from the athlete API. The Next.js `/progress` client renders those responses with React Query and Recharts.

Raw completed workout sets remain the source of truth. Strength results are derived on the backend; no production score is mocked or accepted from the client.

## New analytics flow

1. Resolve week, calendar-month or rolling three-calendar-month boundaries in the authenticated user's timezone.
2. Cap an in-progress period at the requested/local current day and compare it with the same number of elapsed days in the preceding equivalent period.
3. Load only the authenticated athlete's completed sessions and completed sets.
4. Join each set to its exercise and normalized muscle contributions.
5. Calculate eligible Epley estimated strength for weighted sets from 1–12 performed reps. When present, RIR is clamped to 0–5 and added to performed reps as estimated rep potential. This is always labelled “Estimated Strength”, never a true maximum.
6. Calculate externally loaded volume as `load_kg × reps` and allocate it using 1.00 primary and 0.35 secondary contribution weights. Calisthenics use progression difficulty, repetitions/hold time, assistance and optional added load instead of barbell-style e1RM.
7. Aggregate performance, exposure, session frequency, effort quality and exercise diversity per muscle, then compare current, previous and prior-equivalent periods.
8. Return strength cards, muscle rows, trends, balance comparisons, exercise drivers and deterministic recommendations. Existing weight, training-output, readiness and habit analytics remain below this section.

## Database changes

- `muscle_groups`: normalized display name, slug, body region and display order.
- `exercise_muscle_mappings`: exercise-to-muscle role and contribution weight, unique per exercise/muscle.
- `exercise_progressions`: reusable calisthenics progression group, level and difficulty multiplier.
- `strength_reports`: authenticated user, period boundaries, overall score, immutable JSON result, generation time and analytics version.

The seed is idempotent. It normalizes all 151 dataset exercises and maps every exercise to at least one of the supported muscle groups. Alembic owns the reversible schema migration; runtime catalogue seeding only upserts reference data.

## Scoring model (`strength_v1`)

Muscle Strength Score is user-relative and bounded to 0–100:

- 40% strength performance: current per-exercise estimated-strength/calisthenics performance divided by that athlete's historical best, averaged across exercise drivers.
- 25% progression trend: current performance versus the previous equivalent elapsed period, centred at 50 and bounded.
- 15% training exposure: contribution-weighted working sets normalized to a weekly equivalent target of ten sets.
- 10% consistency: distinct relevant sessions normalized to two sessions per week.
- 10% effort quality: quality band derived from recorded RIR/RPE, with a neutral fallback when effort data is absent.

One exercise cannot define a muscle score: exercise-level performance is averaged and confidence exposes limited diversity. Classification requires at least three relevant sessions or six contribution-weighted working sets. Confidence is `insufficient`, `low`, `medium` or `high`; insufficient muscles have a null score and the UI says “Insufficient Data”.

Status bands are Needs Attention (0–39), Developing (40–54), Progressing (55–69), Strong (70–84) and Very Strong (85–100). A medium/high-confidence change of at least 5% is labelled Improving. These labels describe recorded training performance, not biological or medical strength.

## Reports and deterministic insights

Generated reports store the exact `strength_v1` analytics response plus training, recovery and recommendation summaries. Rules cover fast improvement, strong-and-improving areas, insufficient history, low training exposure, push/pull differences and quadriceps/hamstring exposure differences. Recommendations are training guidance only.

Stored report JSON makes a past report reproducible while raw sessions remain authoritative for future recalculation.

## API

- `GET /api/v1/progress/strength?period=week|month|3_months&through=YYYY-MM-DD`
- `GET /api/v1/progress/strength/muscles/{muscle_id}?period=...`
- `POST /api/v1/progress/strength-report` with `{ "period": "month", "through": "YYYY-MM-DD" }`
- `GET /api/v1/progress/strength-reports`
- `GET /api/v1/progress/strength-reports/{report_id}`

All endpoints derive identity from the authenticated session. User IDs are never accepted from the client.

## Frontend components

`StrengthIntelligence` owns the period selector, KPI cards, accessible front/back SVG map, sortable muscle comparison, trend chart, strong/improved/attention panels, balance analysis, muscle detail sheet and report drawer. It is a client component because it needs React Query, charting and interaction. Component-specific responsive styles are isolated in a CSS module; the existing AthleteOS primitives, spacing, colours and typography remain unchanged.

## Known interpretation boundaries

The first version uses Epley estimates only for eligible weighted repetition work. Machines from different manufacturers are compared only to the same exercise in the same user's history. Bodyweight skill scores are progression signals rather than transferable kilogram estimates. Strength Intelligence describes recorded performance and exposure; it does not diagnose anatomy, posture, injury risk or isolated biological muscle strength.
