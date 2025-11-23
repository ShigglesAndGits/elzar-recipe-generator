from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Request Models
class RecipeGenerationRequest(BaseModel):
    """Request model for recipe generation"""
    cuisine: Optional[str] = "No Preference"
    active_profiles: List[str] = Field(default_factory=list)
    prioritize_expiring: bool = False
    time_minutes: int = Field(default=60, ge=15, le=180)
    effort_level: str = "Medium"  # Low, Medium, High
    dish_preference: str = "I don't care"  # No dishes, Few dishes, I don't care
    calories_per_serving: Optional[int] = None
    use_external_ingredients: bool = False
    user_prompt: Optional[str] = None  # Additional user notes


class RecipeResponse(BaseModel):
    """Response model for generated recipe"""
    id: int
    recipe_text: str
    cuisine: Optional[str] = None
    time_minutes: Optional[int] = None
    effort_level: Optional[str] = None
    dish_preference: Optional[str] = None
    calories_per_serving: Optional[int] = None
    used_external_ingredients: bool
    prioritize_expiring: bool
    active_profiles: Optional[str] = None  # JSON string
    created_at: datetime
    llm_model: Optional[str] = None


class RecipeFilter(BaseModel):
    """Filter model for recipe history"""
    cuisine: Optional[str] = None
    min_time: Optional[int] = None
    max_time: Optional[int] = None
    effort_level: Optional[str] = None
    min_calories: Optional[int] = None
    max_calories: Optional[int] = None
    profile_name: Optional[str] = None
    search_text: Optional[str] = None


# Dietary Profile Models
class DietaryProfileCreate(BaseModel):
    """Model for creating a new dietary profile"""
    name: str = Field(..., min_length=1, max_length=100)
    dietary_restrictions: str = Field(..., min_length=1)


class DietaryProfileUpdate(BaseModel):
    """Model for updating a dietary profile"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    dietary_restrictions: Optional[str] = Field(None, min_length=1)


class DietaryProfileResponse(BaseModel):
    """Response model for dietary profile"""
    id: int
    name: str
    dietary_restrictions: str
    created_at: datetime
    updated_at: datetime


# Settings Models
class SettingUpdate(BaseModel):
    """Model for updating a setting"""
    key: str
    value: str


class SettingResponse(BaseModel):
    """Response model for settings"""
    key: str
    value: str
    updated_at: datetime


# Notification Models
class NotificationRequest(BaseModel):
    """Request model for sending notifications"""
    recipe_id: int
    title: Optional[str] = "Recipe from Elzar"

