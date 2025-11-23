from fastapi import APIRouter, HTTPException, status
from typing import List
import json
from datetime import datetime
from pathlib import Path

from ..models import (
    RecipeGenerationRequest,
    RecipeResponse,
    NotificationRequest,
    RecipeIngredient,
    RecipeConsumeRequest,
    RecipeShoppingListRequest,
    RecipeSaveRequest,
    InventoryActionRequest
)
from ..database import db
from ..config import settings
from ..services.grocy_client import GrocyClient
from ..services.llm_client import LLMClient
from ..services.notification import NotificationService
from ..services.inventory_matcher import InventoryMatcher
from ..utils.recipe_parser import (
    extract_metadata_from_recipe,
    format_recipe_for_download
)
from ..utils.config_manager import get_effective_config

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


@router.post("/generate", response_model=RecipeResponse)
async def generate_recipe(request: RecipeGenerationRequest):
    """
    Generate a new recipe based on Grocy inventory and user preferences
    
    BAM! Let's make something delicious! 🌶️
    """
    config = await get_effective_config()
    
    # Initialize clients with effective config
    grocy_client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
    llm_client = LLMClient(config["llm_api_url"], config["llm_api_key"], config["llm_model"])
    
    try:
        # Fetch Grocy inventory
        inventory = await grocy_client.format_inventory_for_llm(
            prioritize_expiring=request.prioritize_expiring
        )
        
        # Get active dietary profiles
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
        
        # Prepare request params for LLM
        request_params = {
            "cuisine": request.cuisine,
            "time_minutes": request.time_minutes,
            "effort_level": request.effort_level,
            "dish_preference": request.dish_preference,
            "calories_per_serving": request.calories_per_serving,
            "use_external_ingredients": request.use_external_ingredients,
            "prioritize_expiring": request.prioritize_expiring,
            "elzar_voice": request.elzar_voice,
            "servings": request.servings,
            "high_leftover_potential": request.high_leftover_potential,
            "user_prompt": request.user_prompt
        }
        
        # Generate recipe with LLM
        recipe_text = await llm_client.generate_recipe(
            inventory=inventory,
            request_params=request_params,
            dietary_profiles=dietary_profiles
        )
        
        # Extract metadata from generated recipe
        extracted_metadata = extract_metadata_from_recipe(recipe_text)
        
        # Prepare recipe data for database
        recipe_data = {
            "recipe_text": recipe_text,
            "cuisine": extracted_metadata.get("cuisine") or request.cuisine,
            "time_minutes": extracted_metadata.get("time_minutes") or request.time_minutes,
            "effort_level": extracted_metadata.get("effort_level") or request.effort_level,
            "dish_preference": request.dish_preference,
            "calories_per_serving": extracted_metadata.get("calories_per_serving") or request.calories_per_serving,
            "used_external_ingredients": request.use_external_ingredients,
            "prioritize_expiring": request.prioritize_expiring,
            "active_profiles": request.active_profiles,
            "grocy_inventory_snapshot": inventory,
            "user_prompt": request.user_prompt,
            "llm_model": config["llm_model"]
        }
        
        # Save to database
        recipe_id = await db.create_recipe(recipe_data)
        
        # Clean up old recipes if needed
        await db.cleanup_old_recipes(config["max_recipe_history"])
        
        # Get the saved recipe
        saved_recipe = await db.get_recipe(recipe_id)
        
        return RecipeResponse(
            id=saved_recipe["id"],
            recipe_text=saved_recipe["recipe_text"],
            cuisine=saved_recipe["cuisine"],
            time_minutes=saved_recipe["time_minutes"],
            effort_level=saved_recipe["effort_level"],
            dish_preference=saved_recipe["dish_preference"],
            calories_per_serving=saved_recipe["calories_per_serving"],
            used_external_ingredients=saved_recipe["used_external_ingredients"],
            prioritize_expiring=saved_recipe["prioritize_expiring"],
            active_profiles=saved_recipe["active_profiles"],
            created_at=saved_recipe["created_at"],
            llm_model=saved_recipe["llm_model"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating recipe: {str(e)}"
        )


@router.post("/regenerate/{recipe_id}", response_model=RecipeResponse)
async def regenerate_recipe(recipe_id: int):
    """
    Regenerate a recipe using the same parameters as a previous recipe
    
    BAM! Let's try something different! 🌶️
    """
    config = await get_effective_config()
    
    # Initialize LLM client
    llm_client = LLMClient(config["llm_api_url"], config["llm_api_key"], config["llm_model"])
    
    try:
        # Get the original recipe
        original = await db.get_recipe(recipe_id)
        if not original:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original recipe not found"
            )
        
        # Reconstruct the inventory snapshot
        inventory = json.loads(original["grocy_inventory_snapshot"])
        
        # Get active dietary profiles
        dietary_profiles = []
        active_profiles = json.loads(original["active_profiles"])
        if active_profiles:
            all_profiles = await db.get_all_profiles()
            dietary_profiles = [
                {
                    "name": p["name"],
                    "dietary_restrictions": p["dietary_restrictions"]
                }
                for p in all_profiles
                if p["name"] in active_profiles
            ]
        
        # Prepare request params
        request_params = {
            "cuisine": original["cuisine"],
            "time_minutes": original["time_minutes"],
            "effort_level": original["effort_level"],
            "dish_preference": original["dish_preference"],
            "calories_per_serving": original["calories_per_serving"],
            "use_external_ingredients": original["used_external_ingredients"],
            "prioritize_expiring": original["prioritize_expiring"],
            "user_prompt": original["user_prompt"]
        }
        
        # Regenerate with the LLM
        recipe_text = await llm_client.regenerate_recipe(
            previous_recipe=original["recipe_text"],
            inventory=inventory,
            request_params=request_params,
            dietary_profiles=dietary_profiles
        )
        
        # Extract metadata
        extracted_metadata = extract_metadata_from_recipe(recipe_text)
        
        # Save new recipe
        recipe_data = {
            "recipe_text": recipe_text,
            "cuisine": extracted_metadata.get("cuisine") or original["cuisine"],
            "time_minutes": extracted_metadata.get("time_minutes") or original["time_minutes"],
            "effort_level": extracted_metadata.get("effort_level") or original["effort_level"],
            "dish_preference": original["dish_preference"],
            "calories_per_serving": extracted_metadata.get("calories_per_serving") or original["calories_per_serving"],
            "used_external_ingredients": original["used_external_ingredients"],
            "prioritize_expiring": original["prioritize_expiring"],
            "active_profiles": active_profiles,
            "grocy_inventory_snapshot": inventory,
            "user_prompt": original["user_prompt"],
            "llm_model": config["llm_model"]
        }
        
        new_recipe_id = await db.create_recipe(recipe_data)
        await db.cleanup_old_recipes(config["max_recipe_history"])
        
        # Get the saved recipe
        saved_recipe = await db.get_recipe(new_recipe_id)
        
        return RecipeResponse(
            id=saved_recipe["id"],
            recipe_text=saved_recipe["recipe_text"],
            cuisine=saved_recipe["cuisine"],
            time_minutes=saved_recipe["time_minutes"],
            effort_level=saved_recipe["effort_level"],
            dish_preference=saved_recipe["dish_preference"],
            calories_per_serving=saved_recipe["calories_per_serving"],
            used_external_ingredients=saved_recipe["used_external_ingredients"],
            prioritize_expiring=saved_recipe["prioritize_expiring"],
            active_profiles=saved_recipe["active_profiles"],
            created_at=saved_recipe["created_at"],
            llm_model=saved_recipe["llm_model"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error regenerating recipe: {str(e)}"
        )


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(recipe_id: int):
    """Get a specific recipe by ID"""
    recipe = await db.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    
    return RecipeResponse(
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


@router.get("/{recipe_id}/download")
async def download_recipe(recipe_id: int):
    """Download recipe as a text file"""
    config = await get_effective_config()
    recipe = await db.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    
    # Format recipe for download
    metadata = {
        "created_at": recipe["created_at"],
        "cuisine": recipe["cuisine"],
        "time_minutes": recipe["time_minutes"],
        "effort_level": recipe["effort_level"],
        "calories_per_serving": recipe["calories_per_serving"],
        "active_profiles": json.loads(recipe["active_profiles"]) if recipe["active_profiles"] else []
    }
    
    formatted_text = format_recipe_for_download(
        recipe["recipe_text"],
        metadata
    )
    
    # Save to file
    export_path = Path(config["recipe_export_path"])
    export_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"recipe_{recipe_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    file_path = export_path / filename
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(formatted_text)
    
    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="text/plain"
    )


@router.post("/{recipe_id}/send")
async def send_recipe_notification(recipe_id: int, notification: NotificationRequest):
    """Send recipe to phone via notification service"""
    config = await get_effective_config()
    notification_service = NotificationService(config["apprise_url"])
    
    if not notification_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Notification service not configured"
        )
    
    recipe = await db.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    
    try:
        success = await notification_service.send_recipe(
            recipe_text=recipe["recipe_text"],
            title=notification.title
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send notification"
            )
        
        return {"status": "success", "message": "Recipe sent successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending notification: {str(e)}"
        )


@router.post("/{recipe_id}/parse-ingredients")
async def parse_recipe_ingredients(recipe_id: int, action_type: str = "consume"):
    """
    Parse recipe ingredients and match them to Grocy products.
    Returns parsed items for user review before taking action.
    
    Args:
        action_type: 'consume', 'shopping', or 'save' - affects quantity conversion
    
    Similar to inventory parsing, this allows users to:
    - Review matched items
    - Create missing products
    - Adjust quantities/units
    - Then proceed with consume/shopping list/save actions
    """
    config = await get_effective_config()
    
    # Get recipe
    recipe = await db.get_recipe(recipe_id)
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
        quantity_units = await grocy_client.get_quantity_units()
        stock_info = await grocy_client.format_inventory_for_llm()
        unit_preference = config.get("unit_preference", "metric")
        
        # Extract and match ingredients using LLM
        # Use shopping list mode for realistic purchasing quantities
        for_shopping_list = (action_type == "shopping")
        ingredients = await matcher.extract_recipe_ingredients(
            recipe["recipe_text"],
            products,
            stock_info,
            unit_preference,
            for_shopping_list=for_shopping_list
        )
        
        print(f"🔍 LLM returned {len(ingredients)} ingredients for action_type='{action_type}'")
        for i, ing in enumerate(ingredients[:3]):  # Show first 3 for debugging
            print(f"  [{i}] product_id={ing.get('product_id')}, product_name={ing.get('product_name')}, quantity={ing.get('quantity')}, unit={ing.get('unit')}")
        
        # Format as ParsedItems (same structure as inventory parser)
        from ..models import ParsedItem
        
        product_name_to_id = {p["name"].lower(): p["id"] for p in products if p.get("name")}
        location_name_to_id = {loc["name"].lower(): loc["id"] for loc in locations if loc.get("name")}
        unit_name_to_id = {unit["name"].lower(): unit["id"] for unit in quantity_units if unit.get("name")}
        
        parsed_items = []
        for ing in ingredients:
            product_id = ing.get("product_id")
            product_name = ing.get("product_name", "")
            
            # If LLM didn't provide product_id, try to match by name
            if not product_id and product_name:
                # Try exact match first
                matched_product = next(
                    (p for p in products if p["name"].lower() == product_name.lower()),
                    None
                )
                if matched_product:
                    product_id = matched_product["id"]
                    product_name = matched_product["name"]
                    print(f"✓ Matched '{ing.get('product_name')}' to product ID {product_id}")
            
            # Determine confidence
            if product_id:
                confidence = "high" if ing.get("in_stock") else "medium"
            else:
                confidence = "new"
            
            # Get location and unit IDs
            location_id = None
            if product_id:
                # Get location from existing product
                product = next((p for p in products if p["id"] == product_id), None)
                if product:
                    location_id = product.get("location_id")
            
            # Guess location for new products
            if not location_id and locations:
                # Default to first location (usually Pantry or Fridge)
                location_id = locations[0]["id"]
            
            # Get unit ID
            unit_str = (ing.get("unit") or "").lower()
            quantity_unit_id = unit_name_to_id.get(unit_str, 2) if unit_str else 2  # Default to Piece
            
            # Ensure quantity and unit are never None
            quantity = ing.get("quantity")
            if quantity is None or not isinstance(quantity, (int, float)):
                quantity = 1.0
            
            unit = ing.get("unit")
            if not unit or not isinstance(unit, str):
                unit = "unit"
            
            parsed_items.append(ParsedItem(
                original_text=ing.get("ingredient_text", ""),
                item_name=product_name or ing.get("ingredient_text", ""),
                quantity=float(quantity),
                unit=str(unit),
                grocy_product_id=product_id,
                grocy_product_name=product_name if product_id else None,
                confidence=confidence,
                location_id=location_id,
                quantity_unit_id=quantity_unit_id
            ))
        
        return {"parsed_items": parsed_items}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing recipe ingredients: {str(e)}"
        )


@router.post("/{recipe_id}/consume-ingredients")
async def consume_recipe_ingredients(recipe_id: int):
    """
    Extract ingredients from recipe and consume them from Grocy stock
    
    This endpoint:
    1. Gets the recipe from database
    2. Uses LLM to extract and match ingredients
    3. Consumes matched ingredients from stock
    4. Returns summary of what was consumed
    """
    config = await get_effective_config()
    
    # Get recipe
    recipe = await db.get_recipe(recipe_id)
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
        stock_info = await grocy_client.format_inventory_for_llm()
        unit_preference = config.get("unit_preference", "metric")
        
        # Extract and match ingredients
        ingredients = await matcher.extract_recipe_ingredients(
            recipe["recipe_text"],
            products,
            stock_info,
            unit_preference
        )
        
        # Consume ingredients that are in stock
        results = {
            "consumed": [],
            "skipped": [],
            "insufficient_stock": []
        }
        
        for ingredient in ingredients:
            if not ingredient.get("product_id"):
                results["skipped"].append({
                    "ingredient": ingredient["ingredient_text"],
                    "reason": "No matching product found"
                })
                continue
            
            if not ingredient.get("in_stock"):
                results["skipped"].append({
                    "ingredient": ingredient["ingredient_text"],
                    "reason": "Not in stock"
                })
                continue
            
            # Check if we have enough stock
            stock_amount = ingredient.get("stock_amount", 0)
            needed_amount = ingredient["quantity"]
            
            if stock_amount < needed_amount:
                results["insufficient_stock"].append({
                    "ingredient": ingredient["ingredient_text"],
                    "needed": needed_amount,
                    "available": stock_amount,
                    "unit": ingredient["unit"]
                })
                # Still consume what we have
                needed_amount = stock_amount
            
            try:
                await grocy_client.consume_product(
                    product_id=ingredient["product_id"],
                    amount=needed_amount
                )
                
                results["consumed"].append({
                    "product_name": ingredient["product_name"],
                    "quantity": needed_amount,
                    "unit": ingredient["unit"]
                })
            except Exception as e:
                results["skipped"].append({
                    "ingredient": ingredient["ingredient_text"],
                    "reason": str(e)
                })
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error consuming ingredients: {str(e)}"
        )


@router.post("/{recipe_id}/add-missing-to-shopping-list")
async def add_missing_to_shopping_list(recipe_id: int):
    """
    Extract ingredients from recipe and add missing ones to Grocy shopping list
    
    This endpoint:
    1. Gets the recipe from database
    2. Uses LLM to extract and match ingredients
    3. Adds missing/insufficient ingredients to shopping list
    4. Returns summary of what was added
    """
    config = await get_effective_config()
    
    # Get recipe
    recipe = await db.get_recipe(recipe_id)
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
        stock_info = await grocy_client.format_inventory_for_llm()
        unit_preference = config.get("unit_preference", "metric")
        
        # Extract and match ingredients
        ingredients = await matcher.extract_recipe_ingredients(
            recipe["recipe_text"],
            products,
            stock_info,
            unit_preference
        )
        
        # Add missing ingredients to shopping list
        results = {
            "added": [],
            "skipped": []
        }
        
        for ingredient in ingredients:
            # Skip if no product match
            if not ingredient.get("product_id"):
                results["skipped"].append({
                    "ingredient": ingredient["ingredient_text"],
                    "reason": "No matching product found - cannot add to shopping list"
                })
                continue
            
            # Check if missing or insufficient
            stock_amount = ingredient.get("stock_amount", 0)
            needed_amount = ingredient["quantity"]
            
            if ingredient.get("in_stock") and stock_amount >= needed_amount:
                # We have enough, skip
                continue
            
            # Calculate how much we need to buy
            amount_to_buy = needed_amount - stock_amount if stock_amount > 0 else needed_amount
            
            try:
                await grocy_client.add_to_shopping_list(
                    product_id=ingredient["product_id"],
                    amount=amount_to_buy,
                    note=f"For recipe: {recipe.get('cuisine', 'Recipe')}"
                )
                
                results["added"].append({
                    "product_name": ingredient["product_name"],
                    "quantity": amount_to_buy,
                    "unit": ingredient["unit"],
                    "reason": "Not in stock" if stock_amount == 0 else f"Insufficient (have {stock_amount})"
                })
            except Exception as e:
                results["skipped"].append({
                    "ingredient": ingredient["ingredient_text"],
                    "reason": str(e)
                })
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding to shopping list: {str(e)}"
        )


@router.post("/{recipe_id}/save-to-grocy")
async def save_recipe_to_grocy(recipe_id: int):
    """
    Save recipe to Grocy as a recipe entity with linked ingredients
    
    This endpoint:
    1. Gets the recipe from database
    2. Uses LLM to extract and match ingredients
    3. Creates recipe in Grocy
    4. Links ingredients to the recipe
    5. Returns Grocy recipe ID
    """
    config = await get_effective_config()
    
    # Get recipe
    recipe = await db.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    
    # Initialize clients
    grocy_client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
    llm_client = LLMClient(
        config["llm_api_url"],
        config["llm_api_key"],
        config["llm_model"]
    )
    matcher = InventoryMatcher(
        config["llm_api_url"],
        config["llm_api_key"],
        config["llm_model"]
    )
    
    try:
        # Format recipe for Grocy (strip Elzar's voice, clean formatting)
        formatted_recipe = await llm_client.format_recipe_for_grocy(recipe["recipe_text"])
        
        # Get Grocy data
        products = await grocy_client.get_products()
        stock_info = await grocy_client.format_inventory_for_llm()
        quantity_units = await grocy_client.get_quantity_units()
        unit_preference = config.get("unit_preference", "metric")
        
        # Create unit lookup
        unit_lookup = {qu["name"].lower(): qu["id"] for qu in quantity_units}
        unit_lookup.update({
            "count": unit_lookup.get("piece", unit_lookup.get("pcs", 1)),
            "g": unit_lookup.get("gram", unit_lookup.get("g", 1)),
            "kg": unit_lookup.get("kilogram", unit_lookup.get("kg", 1)),
            "ml": unit_lookup.get("milliliter", unit_lookup.get("ml", 1)),
            "l": unit_lookup.get("liter", unit_lookup.get("l", 1)),
        })
        
        # Extract and match ingredients (use original recipe for LLM parsing)
        ingredients = await matcher.extract_recipe_ingredients(
            recipe["recipe_text"],
            products,
            stock_info,
            unit_preference
        )
        
        # Extract recipe title from formatted text (first line, remove markdown #)
        recipe_lines = formatted_recipe.split("\n")
        recipe_title = recipe_lines[0].replace("#", "").strip() if recipe_lines else "Elzar Recipe"
        
        # Infer servings from formatted recipe text or use default
        servings = 4  # Default
        for line in recipe_lines[:10]:  # Check first 10 lines
            if "serving" in line.lower():
                # Try to extract number
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    servings = int(numbers[0])
                    break
        
        # Create recipe in Grocy with formatted text
        created_recipe = await grocy_client.create_recipe(
            name=recipe_title,
            description=formatted_recipe,  # Use formatted version
            base_servings=servings
        )
        
        grocy_recipe_id = created_recipe["created_object_id"]
        
        # Add ingredients to recipe
        results = {
            "grocy_recipe_id": grocy_recipe_id,
            "recipe_name": recipe_title,
            "servings": servings,
            "ingredients_added": [],
            "ingredients_skipped": []
        }
        
        for ingredient in ingredients:
            if not ingredient.get("product_id"):
                results["ingredients_skipped"].append({
                    "ingredient": ingredient["ingredient_text"],
                    "reason": "No matching product found"
                })
                continue
            
            # Get quantity unit ID
            unit_str = ingredient.get("unit", "").lower() if ingredient.get("unit") else "unit"
            qu_id = unit_lookup.get(unit_str, 2)  # Default to Piece
            
            try:
                await grocy_client.add_recipe_ingredient(
                    recipe_id=grocy_recipe_id,
                    product_id=ingredient["product_id"],
                    amount=ingredient["quantity"],
                    qu_id=qu_id,
                    note=""
                )
                
                results["ingredients_added"].append({
                    "product_name": ingredient["product_name"],
                    "quantity": ingredient["quantity"],
                    "unit": ingredient["unit"]
                })
            except Exception as e:
                results["ingredients_skipped"].append({
                    "ingredient": ingredient["ingredient_text"],
                    "reason": str(e)
                })
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving recipe to Grocy: {str(e)}"
        )


@router.post("/{recipe_id}/save-to-grocy-reviewed")
async def save_recipe_to_grocy_reviewed(recipe_id: int, request: InventoryActionRequest):
    """
    Save recipe to Grocy with reviewed ingredients
    
    This endpoint:
    1. Gets the recipe from database
    2. Uses LLM to format the recipe cleanly
    3. Creates missing products if requested
    4. Creates recipe in Grocy
    5. Links reviewed ingredients to the recipe
    6. Returns Grocy recipe ID and summary
    """
    config = await get_effective_config()
    
    # Get recipe
    recipe = await db.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    
    # Initialize clients
    grocy_client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
    llm_client = LLMClient(
        config["llm_api_url"],
        config["llm_api_key"],
        config["llm_model"]
    )
    
    try:
        # Format recipe for Grocy (strip Elzar's voice, clean formatting)
        formatted_recipe = await llm_client.format_recipe_for_grocy(recipe["recipe_text"])
        
        # Get Grocy data for product creation
        quantity_units = await grocy_client.get_quantity_units()
        locations = await grocy_client.get_locations()
        default_location_id = locations[0]["id"] if locations else 1
        
        # Create unit lookup
        unit_lookup = {qu["name"].lower(): qu["id"] for qu in quantity_units}
        unit_lookup.update({
            "count": unit_lookup.get("piece", unit_lookup.get("pcs", 1)),
            "g": unit_lookup.get("gram", unit_lookup.get("g", 1)),
            "kg": unit_lookup.get("kilogram", unit_lookup.get("kg", 1)),
            "ml": unit_lookup.get("milliliter", unit_lookup.get("ml", 1)),
            "l": unit_lookup.get("liter", unit_lookup.get("l", 1)),
            "oz": unit_lookup.get("ounce", unit_lookup.get("oz", 1)),
            "lb": unit_lookup.get("pound", unit_lookup.get("lb", 1)),
            "fl oz": unit_lookup.get("fluid ounce", unit_lookup.get("fl oz", 1)),
        })
        
        # Extract recipe title from formatted text
        recipe_lines = formatted_recipe.split("\n")
        recipe_title = recipe_lines[0].replace("#", "").strip() if recipe_lines else "Elzar Recipe"
        
        # Infer servings from formatted recipe text
        servings = 4  # Default
        for line in recipe_lines[:10]:
            if "serving" in line.lower():
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    servings = int(numbers[0])
                    break
        
        # Get all products for unit lookup
        all_products = await grocy_client.get_products()
        product_units = {p["id"]: p.get("qu_id_stock", 1) for p in all_products}
        
        # Process reviewed ingredients - create missing products
        results = {
            "grocy_recipe_id": None,
            "recipe_name": recipe_title,
            "servings": servings,
            "ingredients_added": [],
            "ingredients_skipped": [],
            "created_products": []
        }
        
        processed_ingredients = []
        
        for item in request.items:
            product_id = item.product_id
            
            # Create product if needed
            if item.create_if_missing and not product_id:
                # Get or create unit
                unit_lower = item.unit.lower() if item.unit else "unit"
                qu_id = unit_lookup.get(unit_lower)
                
                if not qu_id:
                    # Try to create common units
                    common_units = {
                        "g": ("Gram", "Grams"),
                        "kg": ("Kilogram", "Kilograms"),
                        "oz": ("Ounce", "Ounces"),
                        "lb": ("Pound", "Pounds"),
                        "ml": ("Milliliter", "Milliliters"),
                        "l": ("Liter", "Liters"),
                        "fl oz": ("Fluid Ounce", "Fluid Ounces"),
                    }
                    
                    if unit_lower in common_units:
                        name, plural = common_units[unit_lower]
                        try:
                            created_unit = await grocy_client.create_quantity_unit(name, plural, unit_lower)
                            qu_id = created_unit["created_object_id"]
                            unit_lookup[unit_lower] = qu_id
                        except Exception as unit_error:
                            if "constraint" in str(unit_error).lower() or "unique" in str(unit_error).lower():
                                existing_units = await grocy_client.get_quantity_units()
                                unit_lookup = {u["name"].lower(): u["id"] for u in existing_units}
                                qu_id = unit_lookup.get(unit_lower) or unit_lookup.get(name.lower())
                    
                    if not qu_id:
                        qu_id = unit_lookup.get("unit", 1)
                
                # Create product
                try:
                    created_product = await grocy_client.create_product(
                        name=item.product_name,
                        location_id=item.location_id or default_location_id,
                        qu_id_stock=qu_id
                    )
                    product_id = created_product["created_object_id"]
                    results["created_products"].append({
                        "name": item.product_name,
                        "id": product_id
                    })
                except Exception as product_error:
                    if "constraint" in str(product_error).lower() or "unique" in str(product_error).lower():
                        products = await grocy_client.get_products()
                        matching_product = next(
                            (p for p in products if p["name"].lower() == item.product_name.lower()),
                            None
                        )
                        if matching_product:
                            product_id = matching_product["id"]
            
            if product_id:
                # Use the product's stock quantity unit to avoid conversion errors
                qu_id = product_units.get(product_id)
                
                # If we don't have the unit (newly created product), refresh the list
                if qu_id is None:
                    # Refresh product list
                    all_products = await grocy_client.get_products()
                    product_units = {p["id"]: p.get("qu_id_stock") for p in all_products}
                    qu_id = product_units.get(product_id)
                
                # If still no unit found, skip this ingredient with a helpful error
                if qu_id is None:
                    results["ingredients_skipped"].append({
                        "ingredient": item.product_name,
                        "reason": f"Product ID {product_id} has no stock unit defined in Grocy"
                    })
                    continue
                
                processed_ingredients.append({
                    "product_id": product_id,
                    "product_name": item.product_name,
                    "amount": item.amount,
                    "unit": item.unit,
                    "qu_id": qu_id
                })
            else:
                results["ingredients_skipped"].append({
                    "ingredient": item.product_name,
                    "reason": "No product ID and creation not enabled"
                })
        
        # Create recipe in Grocy
        created_recipe = await grocy_client.create_recipe(
            name=recipe_title,
            description=formatted_recipe,
            base_servings=servings
        )
        
        grocy_recipe_id = created_recipe["created_object_id"]
        results["grocy_recipe_id"] = grocy_recipe_id
        
        # Add ingredients to recipe
        for ingredient in processed_ingredients:
            try:
                await grocy_client.add_recipe_ingredient(
                    recipe_id=grocy_recipe_id,
                    product_id=ingredient["product_id"],
                    amount=ingredient["amount"],
                    qu_id=ingredient["qu_id"],
                    note=""
                )
                
                results["ingredients_added"].append({
                    "product_name": ingredient["product_name"],
                    "quantity": ingredient["amount"],
                    "unit": ingredient["unit"]
                })
            except Exception as e:
                results["ingredients_skipped"].append({
                    "ingredient": ingredient["product_name"],
                    "reason": str(e)
                })
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving recipe to Grocy: {str(e)}"
        )
