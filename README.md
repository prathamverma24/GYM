# AthleteOS

AthleteOS is a responsive, privacy-first fitness operating system built from the supplied TRD, PRD, implementation plan and Concept 3 UI handoff. It connects a resumable athlete profile to deterministic programming, a dataset-backed 151-exercise library, live workouts, Indian-first nutrition, habits, progress reports, explainable recommendations and optional browser-side pose analysis.

## Stack

- Next.js 16, React 19, TypeScript, Tailwind CSS, TanStack Query and Zustand
- FastAPI, SQLAlchemy 2 and Alembic
- PostgreSQL as the production source of truth; Redis is provisioned for production cache/job growth
- SQLite fallback for a zero-dependency local API run and isolated tests
- Vitest, Pytest and Playwright quality gates

## Run with Docker

```bash
docker compose up --build
```

Open `http://localhost:3000`. The API is at `http://localhost:8000`, with development OpenAPI docs at `http://localhost:8000/docs`.

## Run locally without Docker

Install Node.js 20+, Python 3.11+ and dependencies:

```bash
npm install
python -m pip install -e "apps/api[dev]"
```

Start the API from `apps/api`:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Start the web app from the repository root in another terminal:

```bash
npm run dev
```

The development API creates and seeds a local SQLite database automatically. Copy `.env.example` to `.env` and override values when using PostgreSQL or production-like settings.

## Verify

```bash
cd apps/api
python -m ruff check .
python -m pytest

cd ../..
npm run typecheck
npm run lint
npm run test
npm run build
npm run test:e2e
```

Playwright starts the API and web server when they are not already running. On Linux CI, install its Chromium runtime first with `npx playwright install --with-deps chromium`.

## Repository map

- `apps/web` — product UI, PWA shell, browser-side CV and frontend tests
- `apps/api` — modular API, domain rules, persistence, seed data, migrations and tests
- `docs` — architecture, API, database, security, deployment, CV and food-data decisions
- `docs/EXERCISE_DATASET.md` — workbook import, normalization rules, coverage and exercise-module API
- `docs/IMPLEMENTATION_STATUS.md` — honest requirement-by-requirement completion status
- `docs/REQUIREMENTS_TRACEABILITY.md` — source requirement mapping and verification strategy

Raw scan images are never uploaded or retained by the current product. Derived body ratios are optional, consent-gated and explicitly non-medical.
