from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional

from ..models import RecipeResponse, RecipeFilter
from ..database import db

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/", response_model=List[RecipeResponse])
async def get_recipe_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    cuisine: Optional[str] = None,
    min_time: Optional[int] = None,
    max_time: Optional[int] = None,
    effort_level: Optional[str] = None,
    min_calories: Optional[int] = None,
    max_calories: Optional[int] = None,
    profile_name: Optional[str] = None,
    search_text: Optional[str] = None
):
    """
    Get recipe history with optional filtering and pagination
    """
    filters = {}
    
    if cuisine:
        filters["cuisine"] = cuisine
    if min_time:
        filters["min_time"] = min_time
    if max_time:
        filters["max_time"] = max_time
    if effort_level:
        filters["effort_level"] = effort_level
    if min_calories:
        filters["min_calories"] = min_calories
    if max_calories:
        filters["max_calories"] = max_calories
    if profile_name:
        filters["profile_name"] = profile_name
    if search_text:
        filters["search_text"] = search_text
    
    recipes = await db.get_recipes(
        limit=limit,
        offset=offset,
        filters=filters if filters else None
    )
    
    return [
        RecipeResponse(
            id=recipe["id"],
            recipe_text=recipe["recipe_text"],
            cuisine=recipe["cuisine"],
            time_minutes=recipe["time_minutes"],
            effort_level=recipe["effort_level"],
            dish_preference=recipe["dish_preference"],
            calories_per_serving=recipe["calories_per_serving"],
            used_external_ingredients=recipe["used_external_ingredients"],
            prioritize_expiring=recipe["prioritize_expiring"],
            active_profiles=recipe["active_profiles"],
            created_at=recipe["created_at"],
            llm_model=recipe["llm_model"]
        )
        for recipe in recipes
    ]


@router.delete("/{recipe_id}")
async def delete_recipe(recipe_id: int):
    """Delete a recipe from history"""
    success = await db.delete_recipe(recipe_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    
    return {"status": "success", "message": "Recipe deleted"}


@router.get("/count")
async def get_recipe_count():
    """Get total count of recipes in history"""
    recipes = await db.get_recipes(limit=10000, offset=0)
    return {"count": len(recipes)}

