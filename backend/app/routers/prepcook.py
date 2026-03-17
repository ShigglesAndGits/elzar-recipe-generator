import re
from fastapi import APIRouter, HTTPException, status
from typing import List

from ..models import (
    PrepCookRequest,
    PrepCookSessionResponse,
    PrepCookRecipeResponse,
    PrepCookSessionSummary,
)
from ..database import db
from ..services.grocy_client import GrocyClient
from ..services.llm_client import LLMClient
from ..utils.config_manager import get_effective_config

router = APIRouter(prefix="/api/prepcook", tags=["prepcook"])


def parse_prep_cook_response(raw_text: str, portions_per_meal: int) -> dict:
    """
    Parse LLM response into overview, recipes, timeline, and shopping list.

    Returns:
        Dict with keys: overview, recipes (list), timeline, shopping_list
    """
    result = {
        "overview": "",
        "recipes": [],
        "timeline": "",
        "shopping_list": "",
    }

    # Extract timeline
    timeline_match = re.search(
        r"===TIMELINE===(.*?)===END_TIMELINE===", raw_text, re.DOTALL
    )
    if timeline_match:
        result["timeline"] = timeline_match.group(1).strip()

    # Extract shopping list
    shopping_match = re.search(
        r"===SHOPPING_LIST===(.*?)===END_SHOPPING_LIST===", raw_text, re.DOTALL
    )
    if shopping_match:
        result["shopping_list"] = shopping_match.group(1).strip()

    # Extract recipes
    parts = raw_text.split("===RECIPE===")
    result["overview"] = parts[0].strip()

    # Clean overview: remove timeline/shopping if they ended up before recipes
    for tag in ["===TIMELINE===", "===SHOPPING_LIST==="]:
        if tag in result["overview"]:
            result["overview"] = result["overview"].split(tag)[0].strip()

    for part in parts[1:]:
        recipe_text = part.replace("===END_RECIPE===", "").strip()
        if not recipe_text:
            continue

        title = "Untitled"
        portions = portions_per_meal
        calories = None
        prep_time = None
        estimated_cost = None

        lines = recipe_text.split("\n")
        content_start = 0

        for idx, line in enumerate(lines):
            ls = line.strip()
            upper = ls.upper()

            if upper.startswith("TITLE:"):
                title = ls.split(":", 1)[1].strip()
                content_start = idx + 1
            elif upper.startswith("PORTIONS:"):
                try:
                    portions = int(re.search(r"\d+", ls).group())
                except (AttributeError, ValueError):
                    pass
                content_start = idx + 1
            elif upper.startswith("CALORIES:"):
                try:
                    calories = int(re.search(r"\d+", ls).group())
                except (AttributeError, ValueError):
                    pass
                content_start = idx + 1
            elif upper.startswith("PREP_TIME:"):
                try:
                    prep_time = int(re.search(r"\d+", ls).group())
                except (AttributeError, ValueError):
                    pass
                content_start = idx + 1
            elif upper.startswith("ESTIMATED_COST:"):
                try:
                    cost_match = re.search(r"[\d.]+", ls)
                    if cost_match:
                        estimated_cost = float(cost_match.group())
                except (AttributeError, ValueError):
                    pass
                content_start = idx + 1
            elif ls.startswith("**") or ls.startswith("-") or ls.startswith("1."):
                break

        recipe_content = "\n".join(lines[content_start:]).strip()
        # Remove timeline/shopping if it leaked into recipe content
        for tag in ["===TIMELINE===", "===SHOPPING_LIST==="]:
            if tag in recipe_content:
                recipe_content = recipe_content.split(tag)[0].strip()

        full_text = f"# {title}\n\n{recipe_content}"

        result["recipes"].append({
            "title": title,
            "recipe_text": full_text,
            "portions": portions,
            "calories_per_serving": calories,
            "time_minutes": prep_time,
            "estimated_cost": estimated_cost,
        })

    return result


async def get_user_preferences_text() -> str:
    """Get household preferences text."""
    prefs = await db.get_user_preferences()
    return prefs.get("content", "")


@router.post("/generate", response_model=PrepCookSessionResponse)
async def generate_prep_cook_session(request: PrepCookRequest):
    """
    Generate a prep cook session with multiple freezer-ready recipes,
    a unified prep day timeline, and an aggregated shopping list.
    """
    config = await get_effective_config()

    grocy_configured = bool(config.get("grocy_url") and config.get("grocy_api_key"))

    llm_client = LLMClient(
        config["llm_api_url"],
        config["llm_api_key"],
        config["llm_model"],
        max_tokens=int(config.get("llm_max_tokens", 16000)),
    )

    # Get inventory if configured and requested
    inventory = {"available_items": [], "expiring_soon": []}
    if grocy_configured and request.use_inventory:
        try:
            grocy_client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
            inventory = await grocy_client.format_inventory_for_llm(
                request.prioritize_expiring
            )
        except Exception as e:
            print(f"⚠️ Could not fetch Grocy inventory: {e}")

    # Get dietary profiles
    dietary_profiles = []
    if request.active_profiles:
        all_profiles = await db.get_all_profiles()
        dietary_profiles = [
            p for p in all_profiles if p["name"] in request.active_profiles
        ]

    # Get user preferences
    user_preferences = await get_user_preferences_text()

    # Build request params
    request_params = {
        "num_meals": request.num_meals,
        "portions_per_meal": request.portions_per_meal,
        "protein_anchor": request.protein_anchor,
        "calorie_target": request.calorie_target,
        "available_equipment": request.available_equipment,
        "use_inventory": request.use_inventory,
        "prioritize_expiring": request.prioritize_expiring,
        "user_prompt": request.user_prompt,
        "unit_preference": config.get("unit_preference", "imperial"),
        "custom_persona": config.get(
            "custom_persona", "You are a professional chef and nutritionist."
        ),
    }

    # Generate via LLM
    try:
        raw_text = await llm_client.generate_prep_cook_session(
            inventory, request_params, dietary_profiles, user_preferences
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM generation failed: {str(e)}",
        )

    # Parse the response
    parsed = parse_prep_cook_response(raw_text, request.portions_per_meal)

    if not parsed["recipes"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM did not return any parseable recipes. Try again.",
        )

    # Build recipe data for DB
    db_recipes = []
    for recipe in parsed["recipes"]:
        db_recipes.append({
            "recipe_text": recipe["recipe_text"],
            "cuisine": None,
            "time_minutes": recipe.get("time_minutes"),
            "effort_level": None,
            "calories_per_serving": recipe.get("calories_per_serving"),
            "estimated_cost": recipe.get("estimated_cost"),
        })

    # Save to DB
    session_data = {
        "num_meals": request.num_meals,
        "portions_per_meal": request.portions_per_meal,
        "protein_anchor": request.protein_anchor,
        "calorie_target": request.calorie_target,
        "equipment": request.available_equipment,
        "active_profiles": request.active_profiles,
        "user_prompt": request.user_prompt,
        "overview": parsed["overview"],
        "timeline": parsed["timeline"],
        "shopping_list": parsed["shopping_list"],
        "llm_model": config["llm_model"],
    }

    session_id = await db.create_prep_cook_session(session_data, db_recipes)

    # Fetch back the full session with recipe IDs
    session = await db.get_prep_cook_session(session_id)

    # Build response
    recipe_responses = []
    for i, db_recipe in enumerate(session["recipes"]):
        parsed_recipe = parsed["recipes"][i] if i < len(parsed["recipes"]) else {}
        recipe_responses.append(
            PrepCookRecipeResponse(
                id=db_recipe["id"],
                title=parsed_recipe.get("title", f"Recipe {i+1}"),
                recipe_text=db_recipe["recipe_text"],
                portions=parsed_recipe.get("portions", request.portions_per_meal),
                calories_per_serving=db_recipe.get("calories_per_serving"),
                time_minutes=db_recipe.get("time_minutes"),
                estimated_cost=db_recipe.get("estimated_cost"),
                is_locked=bool(db_recipe.get("is_locked", 0)),
                is_saved=bool(db_recipe.get("is_saved", 0)),
            )
        )

    total_cost = sum(r.estimated_cost or 0 for r in recipe_responses) or None

    return PrepCookSessionResponse(
        id=session_id,
        num_meals=request.num_meals,
        portions_per_meal=request.portions_per_meal,
        protein_anchor=request.protein_anchor,
        calorie_target=request.calorie_target,
        overview=parsed["overview"],
        timeline=parsed["timeline"],
        shopping_list=parsed["shopping_list"],
        recipes=recipe_responses,
        estimated_total_cost=total_cost,
        created_at=session["created_at"],
        llm_model=config["llm_model"],
    )


@router.get("/", response_model=List[PrepCookSessionSummary])
async def get_prep_cook_sessions(limit: int = 20, offset: int = 0):
    """Get prep cook session history."""
    sessions = await db.get_prep_cook_sessions(limit, offset)
    return [
        PrepCookSessionSummary(
            id=s["id"],
            num_meals=s["num_meals"],
            portions_per_meal=s["portions_per_meal"],
            protein_anchor=s.get("protein_anchor"),
            recipe_count=s.get("recipe_count", 0),
            estimated_total_cost=s.get("estimated_total_cost"),
            created_at=s["created_at"],
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=PrepCookSessionResponse)
async def get_prep_cook_session(session_id: int):
    """Get a specific prep cook session with all recipes."""
    session = await db.get_prep_cook_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prep cook session not found",
        )

    recipe_responses = []
    for recipe in session["recipes"]:
        # Extract title from recipe text (first # heading)
        title = "Untitled"
        for line in recipe["recipe_text"].split("\n"):
            if line.strip().startswith("# "):
                title = line.strip()[2:].strip()
                break

        recipe_responses.append(
            PrepCookRecipeResponse(
                id=recipe["id"],
                title=title,
                recipe_text=recipe["recipe_text"],
                portions=session["portions_per_meal"],
                calories_per_serving=recipe.get("calories_per_serving"),
                time_minutes=recipe.get("time_minutes"),
                estimated_cost=recipe.get("estimated_cost"),
                is_locked=bool(recipe.get("is_locked", 0)),
                is_saved=bool(recipe.get("is_saved", 0)),
            )
        )

    total_cost = sum(r.estimated_cost or 0 for r in recipe_responses) or None

    return PrepCookSessionResponse(
        id=session["id"],
        num_meals=session["num_meals"],
        portions_per_meal=session["portions_per_meal"],
        protein_anchor=session.get("protein_anchor"),
        calorie_target=session.get("calorie_target"),
        overview=session.get("overview"),
        timeline=session.get("timeline"),
        shopping_list=session.get("shopping_list"),
        recipes=recipe_responses,
        estimated_total_cost=total_cost,
        created_at=session["created_at"],
        llm_model=session.get("llm_model"),
    )


@router.delete("/{session_id}")
async def delete_prep_cook_session(session_id: int):
    """Delete a prep cook session (recipes stay in history)."""
    success = await db.delete_prep_cook_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prep cook session not found",
        )
    return {"status": "success", "message": "Session deleted (recipes preserved in history)"}
