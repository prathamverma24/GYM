import re
import unicodedata

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domains.workout_dataset import seed_workout_dataset
from app.models import Food, FoodAlias, ServingOption


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return re.sub(r"\s+", " ", value)


EXERCISES = [
    ("Barbell Bench Press", "barbell-bench-press", "Chest", "horizontal_push", ["barbell", "bench"], "intermediate", ["bodybuilding", "aesthetic", "hybrid", "athletic"], "weighted_reps", 4, 6, 10, 150),
    ("Incline Dumbbell Press", "incline-dumbbell-press", "Chest", "horizontal_push", ["dumbbells", "bench"], "beginner", ["bodybuilding", "aesthetic", "hybrid"], "weighted_reps", 3, 8, 12, 120),
    ("Standing Shoulder Press", "standing-shoulder-press", "Shoulders", "vertical_push", ["barbell"], "intermediate", ["bodybuilding", "aesthetic", "hybrid", "athletic"], "weighted_reps", 3, 6, 10, 120),
    ("Dumbbell Lateral Raise", "dumbbell-lateral-raise", "Shoulders", "abduction", ["dumbbells"], "beginner", ["bodybuilding", "aesthetic", "hybrid"], "weighted_reps", 3, 12, 20, 75),
    ("Cable Triceps Pushdown", "cable-triceps-pushdown", "Triceps", "elbow_extension", ["cable_machine"], "beginner", ["bodybuilding", "aesthetic", "hybrid"], "weighted_reps", 3, 10, 15, 75),
    ("Push-up", "push-up", "Chest", "horizontal_push", ["bodyweight"], "beginner", ["bodybuilding", "calisthenics", "aesthetic", "hybrid", "athletic"], "bodyweight_reps", 3, 8, 15, 90),
    ("Knee Push-up", "knee-push-up", "Chest", "horizontal_push", ["bodyweight"], "foundation", ["calisthenics"], "bodyweight_reps", 3, 6, 12, 75),
    ("Diamond Push-up", "diamond-push-up", "Triceps", "horizontal_push", ["bodyweight"], "intermediate", ["calisthenics", "hybrid"], "bodyweight_reps", 3, 6, 12, 90),
    ("Assisted Pull-up", "assisted-pull-up", "Back", "vertical_pull", ["pull_up_bar", "resistance_bands"], "foundation", ["calisthenics", "hybrid"], "assisted_reps", 4, 5, 10, 120),
    ("Pull-up", "pull-up", "Back", "vertical_pull", ["pull_up_bar"], "intermediate", ["calisthenics", "hybrid", "athletic"], "bodyweight_reps", 4, 5, 10, 120),
    ("Dead Hang", "dead-hang", "Back", "vertical_pull", ["pull_up_bar"], "foundation", ["calisthenics"], "isometric_hold", 3, None, None, 75),
    ("Lat Pulldown", "lat-pulldown", "Back", "vertical_pull", ["cable_machine"], "beginner", ["bodybuilding", "aesthetic", "hybrid"], "weighted_reps", 4, 8, 12, 120),
    ("Seated Cable Row", "seated-cable-row", "Back", "horizontal_pull", ["cable_machine"], "beginner", ["bodybuilding", "aesthetic", "hybrid"], "weighted_reps", 3, 8, 12, 120),
    ("One-arm Dumbbell Row", "one-arm-dumbbell-row", "Back", "horizontal_pull", ["dumbbells", "bench"], "beginner", ["bodybuilding", "aesthetic", "hybrid", "athletic"], "weighted_reps", 3, 8, 12, 105),
    ("Band Row", "band-row", "Back", "horizontal_pull", ["resistance_bands"], "beginner", ["bodybuilding", "calisthenics", "aesthetic", "hybrid"], "weighted_reps", 3, 12, 18, 75),
    ("Barbell Curl", "barbell-curl", "Biceps", "elbow_flexion", ["barbell"], "beginner", ["bodybuilding", "aesthetic", "hybrid"], "weighted_reps", 3, 8, 12, 75),
    ("Dumbbell Curl", "dumbbell-curl", "Biceps", "elbow_flexion", ["dumbbells"], "beginner", ["bodybuilding", "aesthetic", "hybrid"], "weighted_reps", 3, 10, 15, 75),
    ("Back Squat", "back-squat", "Legs", "squat", ["barbell", "squat_rack"], "intermediate", ["bodybuilding", "aesthetic", "hybrid", "athletic"], "weighted_reps", 4, 5, 10, 180),
    ("Goblet Squat", "goblet-squat", "Legs", "squat", ["dumbbells"], "beginner", ["bodybuilding", "aesthetic", "hybrid", "athletic"], "weighted_reps", 3, 8, 15, 105),
    ("Bodyweight Squat", "bodyweight-squat", "Legs", "squat", ["bodyweight"], "foundation", ["calisthenics", "athletic", "hybrid"], "bodyweight_reps", 3, 12, 20, 75),
    ("Romanian Deadlift", "romanian-deadlift", "Legs", "hinge", ["barbell"], "intermediate", ["bodybuilding", "aesthetic", "hybrid", "athletic"], "weighted_reps", 3, 6, 10, 150),
    ("Dumbbell Romanian Deadlift", "dumbbell-romanian-deadlift", "Legs", "hinge", ["dumbbells"], "beginner", ["bodybuilding", "aesthetic", "hybrid", "athletic"], "weighted_reps", 3, 8, 12, 120),
    ("Walking Lunge", "walking-lunge", "Legs", "lunge", ["dumbbells"], "beginner", ["bodybuilding", "aesthetic", "hybrid", "athletic"], "weighted_reps", 3, 10, 16, 90),
    ("Reverse Lunge", "reverse-lunge", "Legs", "lunge", ["bodyweight"], "beginner", ["calisthenics", "athletic", "hybrid"], "bodyweight_reps", 3, 8, 15, 90),
    ("Standing Calf Raise", "standing-calf-raise", "Legs", "plantar_flexion", ["bodyweight"], "beginner", ["bodybuilding", "calisthenics", "aesthetic", "hybrid", "athletic"], "bodyweight_reps", 3, 12, 20, 60),
    ("Forearm Plank", "forearm-plank", "Core", "anti_extension", ["bodyweight"], "foundation", ["bodybuilding", "calisthenics", "aesthetic", "hybrid", "athletic"], "isometric_hold", 3, None, None, 60),
    ("Hanging Knee Raise", "hanging-knee-raise", "Core", "core_flexion", ["pull_up_bar"], "intermediate", ["calisthenics", "aesthetic", "hybrid"], "bodyweight_reps", 3, 8, 15, 75),
    ("Parallel-bar Dip", "parallel-bar-dip", "Chest", "vertical_push", ["dip_bars"], "intermediate", ["calisthenics", "hybrid"], "bodyweight_reps", 3, 5, 10, 120),
    ("Box Jump", "box-jump", "Full Body", "jump", ["plyo_box"], "intermediate", ["athletic", "hybrid"], "bodyweight_reps", 4, 3, 5, 120),
    ("Acceleration Sprint", "acceleration-sprint", "Conditioning", "sprint", ["open_space"], "intermediate", ["athletic", "hybrid"], "distance_time", 6, None, None, 120),
    ("Kettlebell Swing", "kettlebell-swing", "Full Body", "hinge", ["kettlebells"], "intermediate", ["athletic", "hybrid"], "weighted_reps", 4, 10, 15, 90),
    ("Farmer Carry", "farmer-carry", "Full Body", "carry", ["dumbbells"], "beginner", ["athletic", "hybrid"], "distance_time", 4, None, None, 90),
    ("L-sit Tuck Hold", "l-sit-tuck-hold", "Core", "skill", ["bodyweight"], "foundation", ["calisthenics"], "isometric_hold", 4, None, None, 75),
    ("Wall Handstand Hold", "wall-handstand-hold", "Shoulders", "skill", ["bodyweight"], "foundation", ["calisthenics"], "isometric_hold", 4, None, None, 90),
]


# Values are transparent per-100 g development estimates. Composite dishes are
# deliberately marked estimated and always shown with serving context.
FOODS = [
    ("Roti", 297, 9.0, 56.0, 4.0, "1 roti", 40, ["chapati", "phulka"]),
    ("Tandoori Roti", 270, 8.5, 52.0, 3.0, "1 roti", 55, []),
    ("Naan", 310, 9.0, 52.0, 8.0, "1 naan", 90, []),
    ("Paratha", 330, 7.0, 45.0, 14.0, "1 paratha", 80, []),
    ("Aloo Paratha", 250, 6.0, 38.0, 8.0, "1 paratha", 120, ["potato paratha"]),
    ("Steamed Rice", 130, 2.7, 28.0, 0.3, "1 bowl", 180, ["rice", "plain rice"]),
    ("Jeera Rice", 170, 3.0, 30.0, 4.5, "1 bowl", 180, ["cumin rice"]),
    ("Brown Rice", 123, 2.7, 25.6, 1.0, "1 bowl", 180, []),
    ("Veg Pulao", 180, 4.0, 31.0, 5.0, "1 bowl", 200, ["vegetable pulao"]),
    ("Poha", 170, 4.0, 30.0, 4.0, "1 bowl", 180, ["kanda poha"]),
    ("Upma", 145, 4.0, 24.0, 4.0, "1 bowl", 180, []),
    ("Idli", 146, 4.5, 30.0, 0.7, "2 idli", 100, ["idly"]),
    ("Dosa", 168, 4.0, 28.0, 4.5, "1 dosa", 120, ["plain dosa"]),
    ("Uttapam", 180, 5.0, 30.0, 4.5, "1 uttapam", 150, ["uthappam"]),
    ("Sambar", 80, 3.8, 12.0, 2.0, "1 bowl", 180, ["sambhar"]),
    ("Aloo Matar Sabzi", 120, 3.3, 19.0, 4.0, "1 bowl", 180, ["aloo matar", "alu matar", "aaloo matar", "aloo mutter", "potato peas curry"]),
    ("Bhindi Sabzi", 110, 3.0, 12.0, 6.0, "1 bowl", 160, ["bhindi", "bhindi masala", "okra", "okra sabzi", "ladyfinger sabzi"]),
    ("Aloo Gobi", 105, 3.0, 15.0, 4.0, "1 bowl", 180, ["potato cauliflower"]),
    ("Mix Veg", 95, 3.0, 13.0, 4.0, "1 bowl", 180, ["mixed vegetable curry"]),
    ("Palak Paneer", 155, 8.0, 7.0, 11.0, "1 bowl", 180, ["spinach paneer"]),
    ("Paneer Bhurji", 190, 12.0, 7.0, 14.0, "1 bowl", 160, ["scrambled paneer"]),
    ("Shahi Paneer", 220, 8.0, 10.0, 17.0, "1 bowl", 180, []),
    ("Matar Paneer", 170, 8.0, 12.0, 11.0, "1 bowl", 180, ["peas paneer"]),
    ("Rajma", 125, 7.0, 20.0, 2.0, "1 bowl", 180, ["kidney bean curry"]),
    ("Rajma Chawal", 160, 5.5, 29.0, 2.5, "1 plate", 320, ["rajma rice"]),
    ("Chole", 160, 7.0, 23.0, 5.0, "1 bowl", 180, ["chana masala", "chickpea curry"]),
    ("Chole Bhature", 290, 8.0, 39.0, 11.0, "1 plate", 300, ["chana bhatura"]),
    ("Dal Tadka", 125, 6.5, 18.0, 3.5, "1 bowl", 180, ["tadka dal", "dal fry"]),
    ("Dal Makhani", 165, 6.0, 19.0, 8.0, "1 bowl", 180, ["black dal"]),
    ("Moong Dal", 105, 7.0, 17.0, 1.5, "1 bowl", 180, ["mung dal"]),
    ("Masoor Dal", 115, 7.5, 18.0, 1.8, "1 bowl", 180, ["red lentil dal"]),
    ("Arhar Dal", 120, 6.5, 18.0, 2.5, "1 bowl", 180, ["toor dal", "tuvar dal"]),
    ("Khichdi", 120, 4.5, 21.0, 2.2, "1 bowl", 220, ["moong dal khichdi"]),
    ("Curd", 61, 3.5, 4.7, 3.3, "1 bowl", 150, ["dahi", "yogurt"]),
    ("Greek Yogurt", 73, 9.0, 4.0, 2.0, "1 bowl", 150, []),
    ("Milk", 61, 3.2, 4.8, 3.3, "1 glass", 250, ["doodh"]),
    ("Buttermilk", 35, 1.5, 4.0, 1.2, "1 glass", 250, ["chaas", "chhach"]),
    ("Lassi", 90, 3.2, 14.0, 2.5, "1 glass", 250, []),
    ("Boiled Egg", 155, 13.0, 1.1, 11.0, "1 egg", 50, ["egg", "boiled eggs"]),
    ("Omelette", 154, 11.0, 2.0, 11.0, "2 egg omelette", 120, ["omelet"]),
    ("Chicken Breast", 165, 31.0, 0.0, 3.6, "1 portion", 150, ["grilled chicken breast"]),
    ("Chicken Curry", 180, 18.0, 6.0, 10.0, "1 bowl", 200, []),
    ("Fish Curry", 150, 18.0, 5.0, 7.0, "1 bowl", 200, []),
    ("Veg Biryani", 190, 4.5, 32.0, 5.5, "1 plate", 280, ["biryani", "vegetable biryani"]),
    ("Chicken Biryani", 210, 11.0, 28.0, 7.0, "1 plate", 320, []),
    ("Banana", 89, 1.1, 23.0, 0.3, "1 medium", 118, []),
    ("Apple", 52, 0.3, 14.0, 0.2, "1 medium", 180, []),
    ("Mango", 60, 0.8, 15.0, 0.4, "1 cup", 165, []),
    ("Orange", 47, 0.9, 12.0, 0.1, "1 medium", 140, []),
    ("Guava", 68, 2.6, 14.0, 1.0, "1 fruit", 100, []),
    ("Papaya", 43, 0.5, 11.0, 0.3, "1 cup", 145, []),
    ("Oats", 379, 13.2, 67.7, 6.5, "1/2 cup dry", 40, ["rolled oats"]),
    ("Peanut Butter", 588, 25.0, 20.0, 50.0, "1 tablespoon", 16, []),
    ("Almonds", 579, 21.0, 22.0, 50.0, "10 almonds", 12, ["badam"]),
    ("Walnuts", 654, 15.0, 14.0, 65.0, "4 halves", 12, ["akhrot"]),
    ("Whey Protein", 390, 78.0, 8.0, 6.0, "1 scoop", 30, ["protein powder"]),
    ("Paneer", 265, 18.0, 3.0, 20.0, "1 portion", 100, ["cottage cheese"]),
    ("Tofu", 144, 17.0, 3.0, 9.0, "1 portion", 100, []),
    ("Soy Chunks", 345, 52.0, 33.0, 0.5, "1 cup cooked", 100, ["soya chunks"]),
    ("Grilled Salmon", 206, 22.0, 0.0, 12.0, "1 fillet", 150, ["salmon"]),
    ("Hummus", 166, 8.0, 14.0, 10.0, "2 tablespoons", 30, []),
]


def seed_catalogues(db: Session) -> None:
    seed_workout_dataset(db)

    if not db.scalar(select(func.count()).select_from(Food)):
        for name, kcal, protein, carbs, fat, serving_label, grams, aliases in FOODS:
            food = Food(
                canonical_name=name,
                normalized_name=normalize_text(name),
                cuisine="indian" if len(aliases) or name in {"Poha", "Upma", "Idli", "Dosa", "Uttapam", "Sambar"} else "global",
                diet_type="non_vegetarian" if any(x in name.lower() for x in ("chicken", "fish", "egg", "salmon")) else "vegetarian",
                energy_kcal=kcal,
                protein_g=protein,
                carb_g=carbs,
                fat_g=fat,
                source="athleteos_curated_development_estimate",
                data_quality="estimated" if name not in {"Banana", "Apple", "Oats", "Milk", "Almonds", "Walnuts"} else "curated",
            )
            db.add(food)
            db.flush()
            db.add(ServingOption(food_id=food.id, label=serving_label, grams=grams, is_default=True))
            for alias in aliases:
                db.add(
                    FoodAlias(
                        food_id=food.id,
                        alias=alias,
                        normalized_alias=normalize_text(alias),
                    )
                )
        db.commit()
