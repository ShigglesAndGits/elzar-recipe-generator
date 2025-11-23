from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any

from ..database import db
from ..config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingValue(BaseModel):
    """Model for setting a value"""
    value: str


class ConfigResponse(BaseModel):
    """Response model for configuration"""
    grocy_url: str
    llm_api_url: str
    llm_model: str
    max_recipe_history: int
    notification_configured: bool


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """Get current application configuration (without sensitive data)"""
    return ConfigResponse(
        grocy_url=settings.grocy_url,
        llm_api_url=settings.llm_api_url,
        llm_model=settings.llm_model,
        max_recipe_history=settings.max_recipe_history,
        notification_configured=settings.apprise_url is not None and settings.apprise_url != ""
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
    
    try:
        client = GrocyClient(settings.grocy_url, settings.grocy_api_key)
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
    
    try:
        client = LLMClient(
            settings.llm_api_url,
            settings.llm_api_key,
            settings.llm_model
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

