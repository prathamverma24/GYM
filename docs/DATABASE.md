# Database

PostgreSQL is the production source of truth. The initial Alembic migration creates identity, athlete, training, nutrition, habits, recommendations, CV and reporting tables with ownership foreign keys and uniqueness constraints.

Important invariants:

- Body metrics are append-only history rows.
- A meal item stores an immutable nutrient snapshot.
- Set writes are unique by workout, prescription, set index and client operation ID.
- Habit completions are unique by athlete, habit and athlete-local date.
- Programs and prescriptions retain their generator/template version.
- Imported exercises retain their workbook source ID/version; split, day and prescription templates preserve the dataset relationship graph.
- Alternative equipment paths are normalized separately so `Bodyweight/Dumbbells` remains an OR choice during programme selection.
- CV feature payloads always carry feature schema/model version and confidence.

The dataset-backed exercise module adds split templates, day templates, day exercise prescriptions, progression rules, selection rules, substitution groups and research-source tables. See `EXERCISE_DATASET.md` for record counts, provenance and import behavior.
