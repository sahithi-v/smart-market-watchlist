from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.auth import get_current_user
from app.db import get_db
from app.models import User, UserSettings
from app.signals.presets import PRESETS, DEFAULT_SENSITIVITY

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsOut(BaseModel):
    sensitivity: str


class SettingsUpdate(BaseModel):
    sensitivity: str

    @field_validator("sensitivity")
    @classmethod
    def valid_sensitivity(cls, v):
        if v not in PRESETS:
            raise ValueError(f"sensitivity must be one of {list(PRESETS)}")
        return v


@router.get("", response_model=SettingsOut)
def get_settings(user: User = Depends(get_current_user), db=Depends(get_db)):
    row = db.query(UserSettings).filter_by(user_id=user.id).first()
    return SettingsOut(sensitivity=row.sensitivity if row else DEFAULT_SENSITIVITY)


@router.patch("", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    # Upsert: a user's UserSettings row doesn't exist until their first save.
    stmt = pg_insert(UserSettings).values(
        user_id=user.id, sensitivity=payload.sensitivity,
    ).on_conflict_do_update(
        index_elements=["user_id"],
        set_={"sensitivity": payload.sensitivity},
    )
    db.execute(stmt)
    db.commit()
    return SettingsOut(sensitivity=payload.sensitivity)