from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from ..database import db
from ..utils.recipe_parser import NUTRIENTS

router = APIRouter(prefix="/api/nutrition", tags=["nutrition"])


@router.get("/nutrients")
async def get_nutrient_list():
    """Return the canonical list of tracked nutrients."""
    return {"nutrients": NUTRIENTS}


@router.get("/overview")
async def get_nutritional_overview(days: int = 14):
    """Get aggregated nutritional overview across recent recipes."""
    overview = await db.get_nutritional_overview(days=days)
    return overview


@router.get("/recipe/{recipe_id}")
async def get_recipe_nutrition(recipe_id: int):
    """Get nutrient ratings for a specific recipe."""
    recipe = await db.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    ratings = await db.get_nutrient_ratings(recipe_id)
    return {"recipe_id": recipe_id, "ratings": ratings}


@router.post("/recipe/{recipe_id}/rate")
async def rate_recipe(recipe_id: int, ratings: Dict[str, int]):
    """Manually set or update nutrient ratings for a recipe."""
    recipe = await db.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Validate nutrients
    valid = {r for r in ratings if r in NUTRIENTS}
    if not valid:
        raise HTTPException(status_code=400, detail="No valid nutrients provided")

    filtered = {k: v for k, v in ratings.items() if k in valid}
    await db.save_nutrient_ratings(recipe_id, filtered)
    return {"message": f"Saved {len(filtered)} nutrient ratings for recipe {recipe_id}"}
