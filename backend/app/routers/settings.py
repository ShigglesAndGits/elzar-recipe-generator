from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ..database import db
from ..config import settings
from ..utils.config_manager import get_effective_config

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingValue(BaseModel):
    """Model for setting a value"""
    value: str


class ConfigResponse(BaseModel):
    """Response model for configuration"""
    grocy_url: str
    grocy_api_key: str  # Masked in response
    llm_api_url: str
    llm_api_key: str    # Masked in response
    llm_model: str
    max_recipe_history: int
    apprise_url: Optional[str] = None
    notification_configured: bool
    unit_preference: str = "metric"  # "metric" or "imperial"


class CoreConfigUpdate(BaseModel):
    """Model for updating core configuration"""
    grocy_url: Optional[str] = None
    grocy_api_key: Optional[str] = None
    llm_api_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    max_recipe_history: Optional[int] = None
    apprise_url: Optional[str] = None
    unit_preference: Optional[str] = None  # "metric" or "imperial"


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """Get current effective configuration"""
    config = await get_effective_config()
    
    # Mask secrets
    grocy_key = config["grocy_api_key"]
    if grocy_key and len(grocy_key) > 8:
        masked_grocy = f"{grocy_key[:4]}...{grocy_key[-4:]}"
    elif grocy_key:
        masked_grocy = "***"
    else:
        masked_grocy = ""
        
    llm_key = config["llm_api_key"]
    if llm_key and len(llm_key) > 8:
        masked_llm = f"{llm_key[:4]}...{llm_key[-4:]}"
    elif llm_key:
        masked_llm = "***"
    else:
        masked_llm = ""
        
    return ConfigResponse(
        grocy_url=config["grocy_url"],
        grocy_api_key=masked_grocy,
        llm_api_url=config["llm_api_url"],
        llm_api_key=masked_llm,
        llm_model=config["llm_model"],
        max_recipe_history=config["max_recipe_history"],
        apprise_url=config["apprise_url"],
        notification_configured=config["apprise_url"] is not None and config["apprise_url"] != "",
        unit_preference=config.get("unit_preference", "metric")
    )


@router.post("/config/update")
async def update_core_config(update: CoreConfigUpdate):
    """
    Update core configuration values in the database.
    These override environment variables and take effect immediately (no restart needed).
    
    Environment variables from .env or docker-compose serve as defaults.
    Database settings override them at runtime.
    """
    try:
        # Validate unit preference if provided
        if update.unit_preference is not None:
            if update.unit_preference not in ["metric", "imperial"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="unit_preference must be 'metric' or 'imperial'"
                )
        
        # Save to database (only if provided and not masked/empty)
        if update.grocy_url is not None and update.grocy_url.strip():
            await db.set_setting("grocy_url", update.grocy_url)
        
        if update.grocy_api_key is not None and update.grocy_api_key != "***" and update.grocy_api_key.strip():
            await db.set_setting("grocy_api_key", update.grocy_api_key)
            
        if update.llm_api_url is not None and update.llm_api_url.strip():
            await db.set_setting("llm_api_url", update.llm_api_url)
            
        if update.llm_api_key is not None and update.llm_api_key != "***" and update.llm_api_key.strip():
            await db.set_setting("llm_api_key", update.llm_api_key)
            
        if update.llm_model is not None:
            await db.set_setting("llm_model", update.llm_model)
            
        if update.max_recipe_history is not None:
            await db.set_setting("max_recipe_history", str(update.max_recipe_history))
            
        if update.apprise_url is not None:
            await db.set_setting("apprise_url", update.apprise_url)
        
        if update.unit_preference is not None:
            await db.set_setting("unit_preference", update.unit_preference)
            
        return {
            "status": "success", 
            "message": "Configuration updated successfully! Changes take effect immediately."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


@router.get("/")
async def get_all_settings() -> Dict[str, str]:
    """Get all user-defined settings from database"""
    return await db.get_all_settings()


@router.get("/{key}")
async def get_setting(key: str) -> Dict[str, Any]:
    """Get a specific setting"""
    value = await db.get_setting(key)
    
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found"
        )
    
    return {"key": key, "value": value}


@router.put("/{key}")
async def set_setting(key: str, setting: SettingValue):
    """Set a setting value"""
    await db.set_setting(key, setting.value)
    return {"status": "success", "key": key, "value": setting.value}


@router.get("/test/grocy")
async def test_grocy_connection():
    """Test Grocy API connection"""
    from ..services.grocy_client import GrocyClient
    
    config = await get_effective_config()
    
    try:
        client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
        stock = await client.get_stock()
        
        return {
            "status": "success",
            "message": "Successfully connected to Grocy",
            "items_count": len(stock)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to Grocy: {str(e)}"
        )


@router.post("/setup-unit-conversions/{system}")
async def setup_unit_conversions(system: str):
    """
    Set up common unit conversions in Grocy
    
    Args:
        system: 'metric' or 'imperial'
    
    Returns:
        Summary of units and conversions created
    """
    if system not in ["metric", "imperial"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System must be 'metric' or 'imperial'"
        )
    
    config = await get_effective_config()
    grocy_client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
    
    results = {
        "units_created": [],
        "units_existing": [],
        "conversions_created": [],
        "conversions_failed": []
    }
    
    try:
        # Get existing units
        existing_units = await grocy_client.get_quantity_units()
        existing_unit_names = {u["name"].lower(): u["id"] for u in existing_units}
        
        # Define common units and conversions
        if system == "metric":
            units_to_create = [
                ("Gram", "Grams", "g"),
                ("Kilogram", "Kilograms", "kg"),
                ("Milliliter", "Milliliters", "ml"),
                ("Liter", "Liters", "l"),
                ("Teaspoon", "Teaspoons", "tsp"),
                ("Tablespoon", "Tablespoons", "tbsp"),
                ("Cup", "Cups", "cup")
            ]
            
            conversions = [
                # Weight
                ("Kilogram", "Gram", 1000),
                # Volume
                ("Liter", "Milliliter", 1000),
                ("Cup", "Milliliter", 240),
                ("Tablespoon", "Milliliter", 15),
                ("Teaspoon", "Milliliter", 5),
            ]
        else:  # imperial
            units_to_create = [
                ("Ounce", "Ounces", "oz"),
                ("Pound", "Pounds", "lb"),
                ("Fluid Ounce", "Fluid Ounces", "fl oz"),
                ("Cup", "Cups", "cup"),
                ("Pint", "Pints", "pt"),
                ("Quart", "Quarts", "qt"),
                ("Gallon", "Gallons", "gal"),
                ("Teaspoon", "Teaspoons", "tsp"),
                ("Tablespoon", "Tablespoons", "tbsp")
            ]
            
            conversions = [
                # Weight
                ("Pound", "Ounce", 16),
                # Volume
                ("Gallon", "Quart", 4),
                ("Quart", "Pint", 2),
                ("Pint", "Cup", 2),
                ("Cup", "Fluid Ounce", 8),
                ("Fluid Ounce", "Tablespoon", 2),
                ("Tablespoon", "Teaspoon", 3),
            ]
        
        # Create units
        unit_id_map = {}
        for name, plural, description in units_to_create:
            if name.lower() in existing_unit_names:
                unit_id_map[name] = existing_unit_names[name.lower()]
                results["units_existing"].append(name)
            else:
                try:
                    created = await grocy_client.create_quantity_unit(
                        name=name,
                        name_plural=plural,
                        description=description
                    )
                    unit_id = created.get("created_object_id")
                    unit_id_map[name] = unit_id
                    results["units_created"].append(name)
                except Exception as e:
                    print(f"Failed to create unit {name}: {e}")
                    continue
        
        # Create conversions
        for from_unit, to_unit, factor in conversions:
            if from_unit in unit_id_map and to_unit in unit_id_map:
                try:
                    await grocy_client.create_quantity_unit_conversion(
                        from_qu_id=unit_id_map[from_unit],
                        to_qu_id=unit_id_map[to_unit],
                        factor=factor
                    )
                    results["conversions_created"].append(f"{from_unit} → {to_unit} (×{factor})")
                except Exception as e:
                    results["conversions_failed"].append(f"{from_unit} → {to_unit}: {str(e)}")
        
        return {
            "status": "success",
            "system": system,
            "summary": {
                "units_created": len(results["units_created"]),
                "units_existing": len(results["units_existing"]),
                "conversions_created": len(results["conversions_created"]),
                "conversions_failed": len(results["conversions_failed"])
            },
            "details": results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup unit conversions: {str(e)}"
        )


@router.get("/test/llm")
async def test_llm_connection():
    """Test LLM API connection"""
    from ..services.llm_client import LLMClient
    
    config = await get_effective_config()
    
    try:
        client = LLMClient(
            config["llm_api_url"],
            config["llm_api_key"],
            config["llm_model"]
        )
        
        # Simple test prompt
        test_inventory = {
            "available_items": [
                {"name": "Tomato", "amount": 3, "unit": "unit"}
            ],
            "expiring_soon": []
        }
        
        test_params = {
            "cuisine": "Italian",
            "time_minutes": 30,
            "effort_level": "Low",
            "dish_preference": "I don't care",
            "calories_per_serving": None,
            "use_external_ingredients": True,
            "prioritize_expiring": False,
            "user_prompt": "Test prompt"
        }
        
        recipe = await client.generate_recipe(
            inventory=test_inventory,
            request_params=test_params,
            dietary_profiles=[]
        )
        
        return {
            "status": "success",
            "message": "Successfully connected to LLM",
            "response_length": len(recipe)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to LLM: {str(e)}"
        )
