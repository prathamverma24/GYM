from datetime import date
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import current_profile
from app.domains.catalog import normalize_text
from app.errors import DomainError
from app.models import (
    AthleteProfile,
    Food,
    FoodAlias,
    Habit,
    HabitCompletion,
    MealItem,
    MealLog,
    ServingOption,
    WaterLog,
)

router = APIRouter(tags=["nutrition"])


class MealItemRequest(BaseModel):
    food_id: str
    serving_id: str | None = None
    quantity: float = Field(gt=0, le=100)
    consumed_grams: float | None = Field(default=None, gt=0, le=10_000)


class MealItemUpdate(BaseModel):
    consumed_grams: float = Field(gt=0, le=10_000)
    serving_label: str = Field(default="custom", max_length=64)


class WaterRequest(BaseModel):
    amount_ml: int = Field(gt=0, le=10_000)
    local_date: date
    client_operation_id: str = Field(min_length=8, max_length=64)


def _food_payload(db: Session, food: Food, score: float | None = None) -> dict:
    servings = db.scalars(select(ServingOption).where(ServingOption.food_id == food.id).order_by(ServingOption.is_default.desc())).all()
    return {
        "id": food.id,
        "canonical_name": food.canonical_name,
        "food_type": food.food_type,
        "cuisine": food.cuisine,
        "diet_type": food.diet_type,
        "per_100g": {
            "energy_kcal": food.energy_kcal,
            "protein_g": food.protein_g,
            "carb_g": food.carb_g,
            "fat_g": food.fat_g,
            "fiber_g": food.fiber_g,
        },
        "source": food.source,
        "data_quality": food.data_quality,
        "servings": [{"id": item.id, "label": item.label, "grams": item.grams, "is_default": item.is_default} for item in servings],
        "search_score": round(score, 3) if score is not None else None,
        "estimate_note": "Prepared-dish nutrition is an estimate; ingredients and oil can change the result." if food.data_quality == "estimated" else None,
    }


@router.get("/foods/search")
def search_foods(q: str = "", limit: int = 20, db: Session = Depends(get_db)):
    limit = max(1, min(50, limit))
    query = normalize_text(q)
    foods = db.scalars(select(Food)).all()
    aliases = db.scalars(select(FoodAlias)).all()
    aliases_by_food: dict[str, list[str]] = {}
    for alias in aliases:
        aliases_by_food.setdefault(alias.food_id, []).append(alias.normalized_alias)
    ranked = []
    for food in foods:
        candidates = [food.normalized_name, *aliases_by_food.get(food.id, [])]
        if not query:
            score = 0.4 if food.cuisine == "indian" else 0.2
        else:
            scores = []
            for candidate in candidates:
                if candidate == query:
                    scores.append(1.0)
                elif candidate.startswith(query):
                    scores.append(0.88)
                elif query in candidate:
                    scores.append(0.78)
                else:
                    scores.append(SequenceMatcher(None, query, candidate).ratio() * 0.68)
            score = max(scores)
        if score >= (0.34 if query else 0):
            if food.data_quality == "curated":
                score += 0.02
            ranked.append((score, food))
    ranked.sort(key=lambda item: (-item[0], item[1].canonical_name))
    return {"query": q, "items": [_food_payload(db, food, score) for score, food in ranked[:limit]]}


@router.get("/foods/{food_id}")
def food_detail(food_id: str, db: Session = Depends(get_db)):
    food = db.get(Food, food_id)
    if not food:
        raise DomainError("FOOD_NOT_FOUND", "Food was not found.", 404)
    return {"food": _food_payload(db, food)}


def _owned_meal(db: Session, profile: AthleteProfile, meal_id: str) -> MealLog:
    meal = db.scalar(select(MealLog).where(MealLog.id == meal_id, MealLog.athlete_id == profile.id))
    if not meal:
        raise DomainError("MEAL_NOT_FOUND", "Meal was not found.", 404)
    return meal


@router.post("/meals/{local_date}/{meal_type}/items", status_code=201)
def add_meal_item(local_date: date, meal_type: str, payload: MealItemRequest, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    if meal_type not in {"breakfast", "lunch", "snacks", "dinner", "custom"}:
        raise DomainError("INVALID_MEAL_TYPE", "Choose a supported meal type.")
    food = db.get(Food, payload.food_id)
    if not food:
        raise DomainError("FOOD_NOT_FOUND", "Food was not found.", 404)
    meal = db.scalar(select(MealLog).where(MealLog.athlete_id == profile.id, MealLog.local_date == local_date, MealLog.meal_type == meal_type))
    if not meal:
        meal = MealLog(athlete_id=profile.id, local_date=local_date, meal_type=meal_type)
        db.add(meal)
        db.flush()
    serving = db.get(ServingOption, payload.serving_id) if payload.serving_id else None
    if serving and serving.food_id != food.id:
        raise DomainError("SERVING_MISMATCH", "Serving does not belong to this food.")
    grams = payload.consumed_grams or ((serving.grams if serving else 100) * payload.quantity)
    factor = grams / 100
    item = MealItem(
        meal_log_id=meal.id,
        food_id=food.id,
        food_name_snapshot=food.canonical_name,
        consumed_grams=grams,
        serving_label=f"{payload.quantity:g} × {serving.label}" if serving else f"{grams:g} g",
        energy_kcal=round(food.energy_kcal * factor, 2),
        protein_g=round(food.protein_g * factor, 2),
        carb_g=round(food.carb_g * factor, 2),
        fat_g=round(food.fat_g * factor, 2),
        source_snapshot=f"{food.source}@{food.source_version}:{food.data_quality}",
    )
    db.add(item)
    db.commit()
    return {"item_id": item.id, "meal_id": meal.id}


@router.patch("/meal-items/{item_id}")
def update_meal_item(item_id: str, payload: MealItemUpdate, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    item = db.scalar(select(MealItem).join(MealLog, MealItem.meal_log_id == MealLog.id).where(MealItem.id == item_id, MealLog.athlete_id == profile.id))
    if not item:
        raise DomainError("MEAL_ITEM_NOT_FOUND", "Meal item was not found.", 404)
    old_grams = item.consumed_grams
    factor = payload.consumed_grams / old_grams
    item.consumed_grams = payload.consumed_grams
    item.serving_label = payload.serving_label
    item.energy_kcal = round(item.energy_kcal * factor, 2)
    item.protein_g = round(item.protein_g * factor, 2)
    item.carb_g = round(item.carb_g * factor, 2)
    item.fat_g = round(item.fat_g * factor, 2)
    db.commit()
    return {"item_id": item.id}


@router.delete("/meal-items/{item_id}", status_code=204)
def delete_meal_item(item_id: str, response: Response, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    item = db.scalar(select(MealItem).join(MealLog, MealItem.meal_log_id == MealLog.id).where(MealItem.id == item_id, MealLog.athlete_id == profile.id))
    if not item:
        raise DomainError("MEAL_ITEM_NOT_FOUND", "Meal item was not found.", 404)
    db.delete(item)
    db.commit()


def nutrition_day_payload(db: Session, profile: AthleteProfile, local_date: date) -> dict:
    meals = db.scalars(select(MealLog).where(MealLog.athlete_id == profile.id, MealLog.local_date == local_date).order_by(MealLog.meal_type)).all()
    result = []
    totals = {"energy_kcal": 0.0, "protein_g": 0.0, "carb_g": 0.0, "fat_g": 0.0}
    for meal in meals:
        items = db.scalars(select(MealItem).where(MealItem.meal_log_id == meal.id).order_by(MealItem.created_at)).all()
        serialized = []
        for item in items:
            for key in totals:
                totals[key] += getattr(item, key)
            serialized.append({
                "id": item.id,
                "food_id": item.food_id,
                "name": item.food_name_snapshot,
                "serving_label": item.serving_label,
                "consumed_grams": item.consumed_grams,
                "energy_kcal": item.energy_kcal,
                "protein_g": item.protein_g,
                "carb_g": item.carb_g,
                "fat_g": item.fat_g,
                "source": item.source_snapshot,
            })
        result.append({"id": meal.id, "meal_type": meal.meal_type, "items": serialized})
    water = sum(db.scalars(select(WaterLog.amount_ml).where(WaterLog.athlete_id == profile.id, WaterLog.local_date == local_date)).all())
    return {
        "date": local_date,
        "totals": {key: round(value, 1) for key, value in totals.items()},
        "targets": {"energy_kcal": 2200, "protein_g": 130, "carb_g": 260, "fat_g": 70, "water_ml": profile.water_target_ml or 3000},
        "water_ml": water,
        "meals": result,
        "target_note": "Targets are editable fitness estimates, not medical prescriptions.",
    }


@router.get("/nutrition/days/{local_date}")
def nutrition_day(local_date: date, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    return nutrition_day_payload(db, profile, local_date)


@router.post("/water", status_code=201)
def add_water(payload: WaterRequest, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    existing = db.scalar(select(WaterLog).where(WaterLog.client_operation_id == payload.client_operation_id))
    if existing:
        if existing.athlete_id != profile.id:
            raise DomainError("IDEMPOTENCY_CONFLICT", "This operation ID belongs to another athlete.", 409)
        return {"id": existing.id, "idempotent_replay": True}
    row = WaterLog(athlete_id=profile.id, **payload.model_dump())
    db.add(row)
    db.commit()
    total = sum(db.scalars(select(WaterLog.amount_ml).where(WaterLog.athlete_id == profile.id, WaterLog.local_date == payload.local_date)).all())
    water_habit = db.scalar(
        select(Habit).where(
            Habit.athlete_id == profile.id,
            Habit.derived_source == "water",
            Habit.active.is_(True),
        )
    )
    if water_habit and total >= (profile.water_target_ml or 3000):
        completion = db.scalar(
            select(HabitCompletion).where(
                HabitCompletion.habit_id == water_habit.id,
                HabitCompletion.athlete_id == profile.id,
                HabitCompletion.local_date == payload.local_date,
            )
        )
        if not completion:
            completion = HabitCompletion(
                habit_id=water_habit.id,
                athlete_id=profile.id,
                local_date=payload.local_date,
            )
            db.add(completion)
        completion.value = 1
        completion.completed = True
        db.commit()
    return {"id": row.id, "day_total_ml": total, "idempotent_replay": False}
