from ..config import settings
from ..database import db

async def get_effective_config():
    """
    Get the effective configuration by merging environment variables (defaults)
    with database settings (runtime overrides).
    
    This allows:
    - Environment variables (from .env or docker-compose) to set defaults
    - Database settings to override at runtime without restart
    - UI changes to take effect immediately
    """
    # Default persona for recipe generation
    default_persona = "You are a professional chef and nutritionist."

    # Start with defaults from env vars
    config = {
        "grocy_url": settings.grocy_url,
        "grocy_api_key": settings.grocy_api_key,
        "llm_api_url": settings.llm_api_url,
        "llm_api_key": settings.llm_api_key,
        "llm_model": settings.llm_model,
        "llm_max_tokens": settings.llm_max_tokens,
        "vision_api_url": settings.vision_api_url or "",
        "vision_api_key": settings.vision_api_key or "",
        "vision_model": settings.vision_model or "",
        "max_recipe_history": settings.max_recipe_history,
        "apprise_url": settings.apprise_url or "",
        "database_path": settings.database_path,
        "recipe_export_path": settings.recipe_export_path,
        "backend_host": settings.backend_host,
        "backend_port": settings.backend_port,
        "unit_preference": settings.unit_preference,
        "custom_persona": default_persona,
    }
    
    # Get runtime overrides from database
    db_settings = await db.get_all_settings()
    
    # Apply database overrides (these take precedence)
    if "grocy_url" in db_settings:
        config["grocy_url"] = db_settings["grocy_url"]
    if "grocy_api_key" in db_settings:
        config["grocy_api_key"] = db_settings["grocy_api_key"]
    if "llm_api_url" in db_settings:
        config["llm_api_url"] = db_settings["llm_api_url"]
    if "llm_api_key" in db_settings:
        config["llm_api_key"] = db_settings["llm_api_key"]
    if "llm_model" in db_settings:
        config["llm_model"] = db_settings["llm_model"]
    if "llm_max_tokens" in db_settings:
        try:
            config["llm_max_tokens"] = int(db_settings["llm_max_tokens"])
        except ValueError:
            pass
    if "vision_api_url" in db_settings:
        config["vision_api_url"] = db_settings["vision_api_url"]
    if "vision_api_key" in db_settings:
        config["vision_api_key"] = db_settings["vision_api_key"]
    if "vision_model" in db_settings:
        config["vision_model"] = db_settings["vision_model"]
    if "max_recipe_history" in db_settings:
        try:
            config["max_recipe_history"] = int(db_settings["max_recipe_history"])
        except ValueError:
            pass
    if "apprise_url" in db_settings:
        config["apprise_url"] = db_settings["apprise_url"]
    if "unit_preference" in db_settings:
        config["unit_preference"] = db_settings["unit_preference"]
    if "custom_persona" in db_settings:
        config["custom_persona"] = db_settings["custom_persona"]

    return config

