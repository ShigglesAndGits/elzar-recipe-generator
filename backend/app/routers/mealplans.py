from fastapi import APIRouter, HTTPException, status
from typing import List
import re
import json

from ..models import (
    MealPlanRequest,
    MealPlanResponse,
    MealPlanRecipe,
    MealPlanSummary,
    ParsedItem
)
from ..database import db
from ..services.grocy_client import GrocyClient
from ..services.llm_client import LLMClient
from ..services.inventory_matcher import InventoryMatcher
from ..utils.config_manager import get_effective_config

router = APIRouter(prefix="/api/mealplans", tags=["mealplans"])


async def require_grocy_configured():
    """Check if Grocy is configured and raise an error if not."""
    config = await get_effective_config()
    if not config.get("grocy_url") or not config.get("grocy_api_key"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grocy is not configured. Please set up Grocy URL and API key in Settings."
        )


def parse_meal_plan_response(raw_text: str, people: int) -> tuple[str, List[dict]]:
    """
    Parse the LLM response into overview and individual recipes.

    Args:
        raw_text: Raw LLM response with ===RECIPE=== delimiters
        people: Number of people (for default servings)

    Returns:
        Tuple of (overview_text, list of recipe dicts)
    """
    recipes = []

    # Split by the recipe delimiter
    parts = raw_text.split("===RECIPE===")

    # First part is the overview
    overview = parts[0].strip() if parts else ""

    # Parse each recipe block
    for i, part in enumerate(parts[1:], 1):
        # Remove end delimiter if present
        recipe_text = part.replace("===END_RECIPE===", "").strip()

        if not recipe_text:
            continue

        # Extract metadata from the beginning of the recipe
        day = 1
        meal_type = "dinner"
        title = f"Recipe {i}"
        calories = None
        prep_time = None
        servings = people
        estimated_cost = None

        lines = recipe_text.split("\n")
        content_start = 0

        for idx, line in enumerate(lines):
            line_stripped = line.strip()

            if line_stripped.upper().startswith("DAY:"):
                try:
                    day = int(re.search(r'\d+', line_stripped).group())
                except (AttributeError, ValueError):
                    pass
                content_start = idx + 1
            elif line_stripped.upper().startswith("MEAL:"):
                meal_type = line_stripped.split(":", 1)[1].strip().lower()
                if meal_type not in ["breakfast", "lunch", "dinner", "snack"]:
                    meal_type = "dinner"
                content_start = idx + 1
            elif line_stripped.upper().startswith("TITLE:"):
                title = line_stripped.split(":", 1)[1].strip()
                content_start = idx + 1
            elif line_stripped.upper().startswith("CALORIES:"):
                try:
                    calories = int(re.search(r'\d+', line_stripped).group())
                except (AttributeError, ValueError):
                    pass
                content_start = idx + 1
            elif line_stripped.upper().startswith("PREP_TIME:"):
                try:
                    prep_time = int(re.search(r'\d+', line_stripped).group())
                except (AttributeError, ValueError):
                    pass
                content_start = idx + 1
            elif line_stripped.upper().startswith("SERVINGS:"):
                try:
                    servings = int(re.search(r'\d+', line_stripped).group())
                except (AttributeError, ValueError):
                    pass
                content_start = idx + 1
            elif line_stripped.upper().startswith("ESTIMATED_COST:"):
                try:
                    # Extract cost value (e.g., "8.50" or "$8.50")
                    cost_match = re.search(r'[\d.]+', line_stripped)
                    if cost_match:
                        estimated_cost = float(cost_match.group())
                except (AttributeError, ValueError):
                    pass
                content_start = idx + 1
            elif line_stripped.startswith("**") or line_stripped.startswith("-") or line_stripped.startswith("1."):
                # Hit the actual recipe content
                break

        # The actual recipe content (ingredients + instructions)
        recipe_content = "\n".join(lines[content_start:]).strip()

        # Build the full recipe text with title
        full_recipe_text = f"# {title}\n\n{recipe_content}"

        recipes.append({
            "day": day,
            "meal_type": meal_type,
            "title": title,
            "recipe_text": full_recipe_text,
            "calories_estimate": calories,
            "prep_time_minutes": prep_time,
            "servings": servings,
            "estimated_cost": estimated_cost
        })

    return overview, recipes


@router.post("/generate", response_model=MealPlanResponse)
async def generate_meal_plan(request: MealPlanRequest):
    """
    Generate a full meal plan based on user preferences.

    This endpoint:
    1. Fetches Grocy inventory if enabled and configured
    2. Builds a comprehensive prompt for the LLM
    3. Parses the response into individual recipes
    4. Saves the meal plan to the database
    5. Returns the structured meal plan
    """
    config = await get_effective_config()

    # Check if Grocy is configured
    grocy_configured = bool(config.get("grocy_url") and config.get("grocy_api_key"))

    # Initialize LLM client
    llm_client = LLMClient(
        config["llm_api_url"],
        config["llm_api_key"],
        config["llm_model"],
        config.get("llm_max_tokens", 16000)
    )

    try:
        # Get inventory if enabled and Grocy is configured
        inventory = {}
        if request.use_inventory and grocy_configured:
            grocy_client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
            try:
                inventory = await grocy_client.format_inventory_for_llm(
                    prioritize_expiring=request.prioritize_expiring
                )
            except Exception as e:
                # Log error but continue without inventory
                print(f"Warning: Could not fetch Grocy inventory for meal plan: {e}")
                inventory = {}

        # Get dietary profiles
        dietary_profiles = []
        if request.active_profiles:
            all_profiles = await db.get_all_profiles()
            dietary_profiles = [
                {
                    "name": p["name"],
                    "dietary_restrictions": p["dietary_restrictions"]
                }
                for p in all_profiles
                if p["name"] in request.active_profiles
            ]

        # Build request params
        request_params = {
            "days": request.days,
            "people": request.people,
            "generate_breakfast": request.generate_breakfast,
            "generate_lunch": request.generate_lunch,
            "generate_dinner": request.generate_dinner,
            "generate_snacks": request.generate_snacks,
            "budget_level": request.budget_level,
            "daily_calorie_target": request.daily_calorie_target,
            "breakfast_effort": request.breakfast_effort,
            "lunch_effort": request.lunch_effort,
            "dinner_effort": request.dinner_effort,
            "snack_effort": request.snack_effort,
            "variety_level": request.variety_level,
            "use_inventory": request.use_inventory,
            "prioritize_expiring": request.prioritize_expiring,
            "user_prompt": request.user_prompt,
            "active_profiles": request.active_profiles,
            "unit_preference": config.get("unit_preference", "imperial"),
            "custom_persona": config.get("custom_persona", "You are a professional chef and nutritionist.")
        }

        # Fetch user preferences
        prefs = await db.get_user_preferences()
        user_preferences = prefs.get("content", "") or ""

        # Generate the meal plan
        raw_plan = await llm_client.generate_meal_plan(
            inventory=inventory,
            request_params=request_params,
            dietary_profiles=dietary_profiles,
            user_preferences=user_preferences
        )

        # Parse the response
        overview, recipes = parse_meal_plan_response(raw_plan, request.people)

        if not recipes:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to parse meal plan. The LLM response did not contain valid recipes."
            )

        # Save to database
        meal_plan_id = await db.create_meal_plan(
            overview=overview,
            recipes=recipes,
            request_params=request_params,
            llm_model=config["llm_model"]
        )

        # Get the saved plan
        saved_plan = await db.get_meal_plan(meal_plan_id)

        # Format response
        formatted_recipes = [
            MealPlanRecipe(
                id=f"day{r['day']}_{r['meal_type']}_{r['id']}",
                day=r["day"],
                meal_type=r["meal_type"],
                title=r["title"],
                recipe_text=r["recipe_text"],
                calories_estimate=r["calories_estimate"],
                prep_time_minutes=r["prep_time_minutes"],
                servings=r["servings"] or request.people,
                estimated_cost=r.get("estimated_cost")
            )
            for r in saved_plan["recipes"]
        ]

        # Calculate total estimated cost
        total_cost = sum(
            r.estimated_cost for r in formatted_recipes
            if r.estimated_cost is not None
        )
        estimated_total_cost = total_cost if total_cost > 0 else None

        return MealPlanResponse(
            id=saved_plan["id"],
            overview=saved_plan["overview"],
            recipes=formatted_recipes,
            total_days=saved_plan["total_days"],
            total_people=saved_plan["total_people"],
            budget_level=saved_plan["budget_level"],
            estimated_total_cost=estimated_total_cost,
            created_at=saved_plan["created_at"],
            llm_model=saved_plan["llm_model"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating meal plan: {str(e)}"
        )


@router.get("/", response_model=List[MealPlanSummary])
async def get_meal_plans(limit: int = 20, offset: int = 0):
    """Get list of meal plan summaries"""
    plans = await db.get_meal_plans(limit=limit, offset=offset)

    return [
        MealPlanSummary(
            id=p["id"],
            total_days=p["total_days"],
            total_people=p["total_people"],
            budget_level=p["budget_level"],
            meal_count=p["meal_count"],
            estimated_total_cost=p.get("estimated_total_cost"),
            created_at=p["created_at"]
        )
        for p in plans
    ]


@router.get("/{meal_plan_id}", response_model=MealPlanResponse)
async def get_meal_plan(meal_plan_id: int):
    """Get a specific meal plan with all recipes"""
    plan = await db.get_meal_plan(meal_plan_id)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found"
        )

    formatted_recipes = [
        MealPlanRecipe(
            id=f"day{r['day']}_{r['meal_type']}_{r['id']}",
            day=r["day"],
            meal_type=r["meal_type"],
            title=r["title"],
            recipe_text=r["recipe_text"],
            calories_estimate=r["calories_estimate"],
            prep_time_minutes=r["prep_time_minutes"],
            servings=r["servings"] or plan["total_people"],
            estimated_cost=r.get("estimated_cost")
        )
        for r in plan["recipes"]
    ]

    # Calculate total estimated cost
    total_cost = sum(
        r.estimated_cost for r in formatted_recipes
        if r.estimated_cost is not None
    )
    estimated_total_cost = total_cost if total_cost > 0 else None

    return MealPlanResponse(
        id=plan["id"],
        overview=plan["overview"],
        recipes=formatted_recipes,
        total_days=plan["total_days"],
        total_people=plan["total_people"],
        budget_level=plan["budget_level"],
        estimated_total_cost=estimated_total_cost,
        created_at=plan["created_at"],
        llm_model=plan["llm_model"]
    )


@router.delete("/{meal_plan_id}")
async def delete_meal_plan(meal_plan_id: int):
    """Delete a meal plan"""
    success = await db.delete_meal_plan(meal_plan_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found"
        )

    return {"status": "success", "message": "Meal plan deleted"}


@router.get("/{meal_plan_id}/recipes/{recipe_id}")
async def get_meal_plan_recipe(meal_plan_id: int, recipe_id: int):
    """Get a specific recipe from a meal plan"""
    recipe = await db.get_meal_plan_recipe(meal_plan_id, recipe_id)

    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )

    return MealPlanRecipe(
        id=f"day{recipe['day']}_{recipe['meal_type']}_{recipe['id']}",
        day=recipe["day"],
        meal_type=recipe["meal_type"],
        title=recipe["title"],
        recipe_text=recipe["recipe_text"],
        calories_estimate=recipe["calories_estimate"],
        prep_time_minutes=recipe["prep_time_minutes"],
        servings=recipe["servings"],
        estimated_cost=recipe.get("estimated_cost")
    )


@router.post("/{meal_plan_id}/recipes/{recipe_id}/regenerate")
async def regenerate_meal_plan_recipe(meal_plan_id: int, recipe_id: int):
    """
    Regenerate a single recipe in a meal plan.

    This endpoint generates a new recipe for the specified slot while maintaining
    context about other recipes in the plan (ingredients, etc.)
    """
    config = await get_effective_config()

    # Get the meal plan
    plan = await db.get_meal_plan(meal_plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found"
        )

    # Find the recipe to regenerate
    target_recipe = None
    other_recipes = []
    for r in plan["recipes"]:
        if r["id"] == recipe_id:
            target_recipe = r
        else:
            other_recipes.append(r)

    if not target_recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found in meal plan"
        )

    # Get original request params
    request_params = await db.get_meal_plan_request_params(meal_plan_id)
    if not request_params:
        request_params = {
            "people": plan["total_people"],
            "budget_level": plan["budget_level"],
            "unit_preference": config.get("unit_preference", "imperial")
        }

    # Get dietary profiles
    dietary_profiles = []
    active_profile_names = request_params.get("active_profiles", [])
    if active_profile_names:
        all_profiles = await db.get_all_profiles()
        dietary_profiles = [
            {"name": p["name"], "dietary_restrictions": p["dietary_restrictions"]}
            for p in all_profiles
            if p["name"] in active_profile_names
        ]

    # Get inventory if enabled
    inventory = {}
    grocy_configured = bool(config.get("grocy_url") and config.get("grocy_api_key"))
    if request_params.get("use_inventory") and grocy_configured:
        try:
            grocy_client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
            inventory = await grocy_client.format_inventory_for_llm(
                prioritize_expiring=request_params.get("prioritize_expiring", False)
            )
        except Exception:
            pass  # Continue without inventory

    # Generate new recipe
    llm_client = LLMClient(config["llm_api_url"], config["llm_api_key"], config["llm_model"])

    try:
        # Fetch user preferences
        prefs = await db.get_user_preferences()
        user_preferences = prefs.get("content", "") or ""

        raw_recipe = await llm_client.regenerate_meal_plan_recipe(
            day=target_recipe["day"],
            meal_type=target_recipe["meal_type"],
            other_recipes=other_recipes,
            request_params=request_params,
            dietary_profiles=dietary_profiles,
            inventory=inventory,
            old_recipe_text=target_recipe.get("recipe_text"),
            user_preferences=user_preferences
        )

        # Parse the new recipe
        _, new_recipes = parse_meal_plan_response(raw_recipe, plan["total_people"])

        if not new_recipes:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to parse regenerated recipe"
            )

        new_recipe_data = new_recipes[0]

        # Update the database
        await db.update_meal_plan_recipe(
            meal_plan_id=meal_plan_id,
            recipe_id=recipe_id,
            recipe_data=new_recipe_data
        )

        # Return the updated recipe
        return MealPlanRecipe(
            id=f"day{target_recipe['day']}_{target_recipe['meal_type']}_{recipe_id}",
            day=target_recipe["day"],
            meal_type=target_recipe["meal_type"],
            title=new_recipe_data["title"],
            recipe_text=new_recipe_data["recipe_text"],
            calories_estimate=new_recipe_data.get("calories_estimate"),
            prep_time_minutes=new_recipe_data.get("prep_time_minutes"),
            servings=new_recipe_data.get("servings", plan["total_people"]),
            estimated_cost=new_recipe_data.get("estimated_cost")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error regenerating recipe: {str(e)}"
        )


@router.post("/{meal_plan_id}/recipes/{recipe_id}/parse-ingredients")
async def parse_meal_plan_recipe_ingredients(
    meal_plan_id: int,
    recipe_id: int,
    action_type: str = "consume"
):
    """
    Parse ingredients from a meal plan recipe and match to Grocy products.
    """
    await require_grocy_configured()
    config = await get_effective_config()

    # Get the recipe
    recipe = await db.get_meal_plan_recipe(meal_plan_id, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )

    # Initialize clients
    grocy_client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
    matcher = InventoryMatcher(
        config["llm_api_url"],
        config["llm_api_key"],
        config["llm_model"]
    )

    try:
        # Get Grocy data
        products = await grocy_client.get_products()
        locations = await grocy_client.get_locations()
        stock = await grocy_client.get_stock()

        # Create stock lookup
        stock_by_product = {}
        for item in stock:
            pid = item.get("product_id")
            if pid:
                stock_by_product[pid] = item.get("amount", 0)

        # Parse recipe ingredients
        parsed_items = await matcher.parse_recipe_ingredients(
            recipe_text=recipe["recipe_text"],
            products=products,
            locations=locations,
            action_type=action_type
        )

        # Add stock info to parsed items
        for item in parsed_items:
            if item.product_id:
                item.current_stock = stock_by_product.get(item.product_id, 0)

        return parsed_items

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing recipe ingredients: {str(e)}"
        )


@router.post("/{meal_plan_id}/recipes/{recipe_id}/consume-ingredients")
async def consume_meal_plan_recipe_ingredients(meal_plan_id: int, recipe_id: int):
    """
    Consume ingredients from a meal plan recipe from Grocy stock.
    """
    await require_grocy_configured()
    config = await get_effective_config()

    # Get the recipe
    recipe = await db.get_meal_plan_recipe(meal_plan_id, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )

    # Initialize clients
    grocy_client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
    matcher = InventoryMatcher(
        config["llm_api_url"],
        config["llm_api_key"],
        config["llm_model"]
    )

    try:
        # Get Grocy data
        products = await grocy_client.get_products()
        locations = await grocy_client.get_locations()
        stock = await grocy_client.get_stock()

        # Create stock lookup
        stock_by_product = {}
        for item in stock:
            pid = item.get("product_id")
            if pid:
                stock_by_product[pid] = item.get("amount", 0)

        # Parse recipe ingredients
        parsed_items = await matcher.parse_recipe_ingredients(
            recipe_text=recipe["recipe_text"],
            products=products,
            locations=locations,
            action_type="consume"
        )

        # Consume matched items
        results = {"consumed": [], "skipped": [], "errors": []}

        for item in parsed_items:
            if not item.product_id:
                results["skipped"].append({
                    "name": item.raw_text,
                    "reason": "No matching product found"
                })
                continue

            current_stock = stock_by_product.get(item.product_id, 0)
            if current_stock <= 0:
                results["skipped"].append({
                    "name": item.matched_product_name or item.raw_text,
                    "reason": "No stock available"
                })
                continue

            # Consume the amount (or what's available)
            consume_amount = min(item.quantity, current_stock)

            try:
                await grocy_client.consume_product(
                    product_id=item.product_id,
                    amount=consume_amount
                )
                results["consumed"].append({
                    "name": item.matched_product_name,
                    "amount": consume_amount,
                    "unit": item.unit
                })
            except Exception as e:
                results["errors"].append({
                    "name": item.matched_product_name or item.raw_text,
                    "error": str(e)
                })

        return results

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error consuming ingredients: {str(e)}"
        )


@router.post("/{meal_plan_id}/recipes/{recipe_id}/add-missing-to-shopping-list")
async def add_meal_plan_recipe_missing_to_shopping(meal_plan_id: int, recipe_id: int):
    """
    Add missing ingredients from a meal plan recipe to shopping list.
    """
    await require_grocy_configured()
    config = await get_effective_config()

    # Get the recipe
    recipe = await db.get_meal_plan_recipe(meal_plan_id, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )

    # Initialize clients
    grocy_client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
    matcher = InventoryMatcher(
        config["llm_api_url"],
        config["llm_api_key"],
        config["llm_model"]
    )

    try:
        # Get Grocy data
        products = await grocy_client.get_products()
        locations = await grocy_client.get_locations()
        stock = await grocy_client.get_stock()

        # Create stock lookup
        stock_by_product = {}
        for item in stock:
            pid = item.get("product_id")
            if pid:
                stock_by_product[pid] = item.get("amount", 0)

        # Parse recipe ingredients
        parsed_items = await matcher.parse_recipe_ingredients(
            recipe_text=recipe["recipe_text"],
            products=products,
            locations=locations,
            action_type="shopping"
        )

        # Add missing items to shopping list
        results = {"added": [], "skipped": [], "errors": []}

        for item in parsed_items:
            if item.product_id:
                current_stock = stock_by_product.get(item.product_id, 0)
                if current_stock >= item.quantity:
                    results["skipped"].append({
                        "name": item.matched_product_name,
                        "reason": "Sufficient stock"
                    })
                    continue

                needed = item.quantity - current_stock
                try:
                    await grocy_client.add_to_shopping_list(
                        product_id=item.product_id,
                        amount=needed,
                        note=f"For: {recipe['title']}"
                    )
                    results["added"].append({
                        "name": item.matched_product_name,
                        "amount": needed,
                        "unit": item.unit
                    })
                except Exception as e:
                    results["errors"].append({
                        "name": item.matched_product_name,
                        "error": str(e)
                    })
            else:
                # No product match - add as note
                results["skipped"].append({
                    "name": item.raw_text,
                    "reason": "No matching product - add manually"
                })

        return results

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding to shopping list: {str(e)}"
        )


@router.post("/{meal_plan_id}/recipes/{recipe_id}/save-to-grocy")
async def save_meal_plan_recipe_to_grocy(meal_plan_id: int, recipe_id: int):
    """
    Save a meal plan recipe to Grocy as a recipe entity with linked ingredients.
    """
    await require_grocy_configured()
    config = await get_effective_config()

    # Get the recipe
    recipe = await db.get_meal_plan_recipe(meal_plan_id, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )

    # Initialize clients
    grocy_client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
    llm_client = LLMClient(config["llm_api_url"], config["llm_api_key"], config["llm_model"])
    matcher = InventoryMatcher(
        config["llm_api_url"],
        config["llm_api_key"],
        config["llm_model"]
    )

    try:
        # Get Grocy data
        products = await grocy_client.get_products()
        locations = await grocy_client.get_locations()

        # Format recipe text for Grocy (strip any voice/personality)
        formatted_recipe = await llm_client.format_recipe_for_grocy(recipe["recipe_text"])

        # Parse ingredients
        parsed_items = await matcher.parse_recipe_ingredients(
            recipe_text=recipe["recipe_text"],
            products=products,
            locations=locations,
            action_type="save"
        )

        # Create recipe in Grocy
        grocy_recipe_id = await grocy_client.create_recipe(
            name=recipe["title"],
            description=formatted_recipe,
            servings=recipe.get("servings", 2)
        )

        # Link ingredients to the recipe
        linked_ingredients = []
        skipped_ingredients = []

        for item in parsed_items:
            if item.product_id:
                try:
                    await grocy_client.add_recipe_ingredient(
                        recipe_id=grocy_recipe_id,
                        product_id=item.product_id,
                        amount=item.quantity,
                        note=item.raw_text
                    )
                    linked_ingredients.append(item.matched_product_name)
                except Exception as e:
                    skipped_ingredients.append({
                        "name": item.matched_product_name or item.raw_text,
                        "error": str(e)
                    })
            else:
                skipped_ingredients.append({
                    "name": item.raw_text,
                    "reason": "No matching product"
                })

        return {
            "grocy_recipe_id": grocy_recipe_id,
            "linked_ingredients": len(linked_ingredients),
            "skipped_ingredients": len(skipped_ingredients),
            "message": f"Recipe '{recipe['title']}' saved to Grocy with {len(linked_ingredients)} ingredients linked"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving recipe to Grocy: {str(e)}"
        )
