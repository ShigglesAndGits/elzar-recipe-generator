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
    Update core configuration values by writing directly to .env file.
    This ensures persistence across restarts.
    """
    try:
        from pathlib import Path
        import os
        
        # Validate unit preference if provided
        if update.unit_preference is not None:
            if update.unit_preference not in ["metric", "imperial"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="unit_preference must be 'metric' or 'imperial'"
                )
        
        # Get current config to preserve unmodified values
        config = await get_effective_config()
        
        # Update with new values (only if provided and not masked)
        if update.grocy_url is not None:
            config["grocy_url"] = update.grocy_url
        if update.grocy_api_key is not None and update.grocy_api_key != "***":
            config["grocy_api_key"] = update.grocy_api_key
        if update.llm_api_url is not None:
            config["llm_api_url"] = update.llm_api_url
        if update.llm_api_key is not None and update.llm_api_key != "***":
            config["llm_api_key"] = update.llm_api_key
        if update.llm_model is not None:
            config["llm_model"] = update.llm_model
        if update.max_recipe_history is not None:
            config["max_recipe_history"] = update.max_recipe_history
        if update.apprise_url is not None:
            config["apprise_url"] = update.apprise_url
        if update.unit_preference is not None:
            config["unit_preference"] = update.unit_preference
        
        # Write to .env file
        env_path = Path(__file__).parent.parent / ".env"
        
        env_content = f"""GROCY_URL={config['grocy_url']}
GROCY_API_KEY={config['grocy_api_key']}
LLM_API_URL={config['llm_api_url']}
LLM_API_KEY={config['llm_api_key']}
LLM_MODEL={config['llm_model']}
MAX_RECIPE_HISTORY={config['max_recipe_history']}
DATABASE_PATH={config.get('database_path', '../data/recipes.db')}
RECIPE_EXPORT_PATH={config.get('recipe_export_path', '../data/recipes')}
APPRISE_URL={config.get('apprise_url', '')}
BACKEND_HOST={config.get('backend_host', '0.0.0.0')}
BACKEND_PORT={config.get('backend_port', 8000)}
UNIT_PREFERENCE={config.get('unit_preference', 'metric')}
"""
        
        print(f"🔧 Writing config to: {env_path}")
        print(f"📝 Config content preview: GROCY_API_KEY={'[SET]' if config['grocy_api_key'] else '[EMPTY]'}, UNIT_PREFERENCE={config.get('unit_preference', 'metric')}")
        
        with open(env_path, 'w') as f:
            f.write(env_content)
        
        print(f"✅ Config written successfully to {env_path}")
        
        return {
            "status": "success", 
            "message": "Configuration saved to .env file. Restart backend to apply changes."
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
