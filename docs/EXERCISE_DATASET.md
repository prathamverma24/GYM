# Exercise Dataset Module

The exercise module is generated from `AthleteOS_Gym_Workout_Dataset_v1.xlsx`. The workbook remains the editable source; the API reads the validated runtime artifact at `apps/api/app/data/workout_dataset_v1.json`.

## Coverage

| Dataset area | Records |
| --- | ---: |
| Exercises | 151 |
| Split templates | 30 |
| Program-day templates | 116 |
| Day exercise prescriptions | 691 |
| Progression rules | 10 |
| Selection rules | 18 |
| Substitution groups | 16 |
| Research sources | 8 |

Source SHA-256: `8d00e714d3ee8c2139cd43aea2104151a9b84c71846af5b617128482a03b63c7`.

## Importing a revised workbook

Install the API development dependencies, then run from the repository root:

```bash
python scripts/import_workout_dataset.py AthleteOS_Gym_Workout_Dataset_v1.xlsx apps/api/app/data/workout_dataset_v1.json
```

The importer rejects duplicate identifiers and broken split, day, exercise, progression, substitution, or exercise-name references. Application startup idempotently upserts the validated artifact into the database.

## Data interpretation

- Slash-separated equipment, such as `Bodyweight/Dumbbells`, represents alternatives. The normalized `equipment_options` field preserves that OR relationship for filtering and plan generation.
- Exercise records retain their workbook identifier in `source_id`, plus the source version and original row metadata for traceability.
- Programme prescriptions connect exercises to their split/day, set and rep targets, rest, intensity, progression rule and optional substitution group.
- The workbook does not provide detailed coaching instructions for every exercise. AthleteOS supplies short neutral setup and safety guidance without claiming it came from the source.
- Research references are exposed as dataset provenance; they are not used to claim medical validation or individualized clinical advice.

## API surface

- `GET /api/v1/exercises` — paginated search and filters with catalogue facets.
- `GET /api/v1/exercises/{exercise_id}` — complete exercise profile, programme usages, substitutions and progression rules.
- `GET /api/v1/exercise-module` — dataset counts, split summaries and research provenance.
