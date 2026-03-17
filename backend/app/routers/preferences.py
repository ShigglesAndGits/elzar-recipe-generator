from fastapi import APIRouter

from ..models import UserPreferencesUpdate, UserPreferencesResponse
from ..database import db

router = APIRouter(prefix="/api/preferences", tags=["preferences"])


@router.get("/", response_model=UserPreferencesResponse)
async def get_preferences():
    """Get the user preference profile document"""
    prefs = await db.get_user_preferences()
    return UserPreferencesResponse(
        content=prefs["content"],
        updated_at=prefs["updated_at"]
    )


@router.put("/", response_model=UserPreferencesResponse)
async def update_preferences(update: UserPreferencesUpdate):
    """Update the user preference profile document"""
    prefs = await db.set_user_preferences(content=update.content)
    return UserPreferencesResponse(
        content=prefs["content"],
        updated_at=prefs["updated_at"]
    )
