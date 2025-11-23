from fastapi import APIRouter, HTTPException, status
from typing import List
import json
from datetime import datetime
from pathlib import Path

from ..models import (
    RecipeGenerationRequest,
    RecipeResponse,
    NotificationRequest
)
from ..database import db
from ..config import settings
from ..services.grocy_client import GrocyClient
from ..services.llm_client import LLMClient
from ..services.notification import NotificationService
from ..utils.recipe_parser import (
    extract_metadata_from_recipe,
    format_recipe_for_download
)

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

# Initialize clients
grocy_client = GrocyClient(settings.grocy_url, settings.grocy_api_key)
llm_client = LLMClient(settings.llm_api_url, settings.llm_api_key, settings.llm_model)
notification_service = NotificationService(settings.apprise_url)


@router.post("/generate", response_model=RecipeResponse)
async def generate_recipe(request: RecipeGenerationRequest):
    """
    Generate a new recipe based on Grocy inventory and user preferences
    
    BAM! Let's make something delicious! 🌶️
    """
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
            "llm_model": settings.llm_model
        }
        
        # Save to database
        recipe_id = await db.create_recipe(recipe_data)
        
        # Clean up old recipes if needed
        await db.cleanup_old_recipes(settings.max_recipe_history)
        
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
            "llm_model": settings.llm_model
        }
        
        new_recipe_id = await db.create_recipe(recipe_data)
        await db.cleanup_old_recipes(settings.max_recipe_history)
        
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
    export_path = Path(settings.recipe_export_path)
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

