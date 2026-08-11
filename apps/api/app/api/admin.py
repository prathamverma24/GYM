from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import admin_user
from app.models import Exercise, Food, User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview")
def overview(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    return {
        "users": db.scalar(select(func.count()).select_from(User)),
        "foods": db.scalar(select(func.count()).select_from(Food)),
        "exercises": db.scalar(select(func.count()).select_from(Exercise)),
        "catalogue_version": "athleteos_curated_v1",
        "jobs": {"failed": 0, "queued": 0},
    }

