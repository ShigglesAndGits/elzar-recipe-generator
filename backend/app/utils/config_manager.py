from ..config import settings
from ..database import db

async def get_effective_config():
    """
    Get the effective configuration by merging environment variables (defaults)
    with database settings (overrides).
    """
    # Start with defaults from env vars
    config = {
        "grocy_url": settings.grocy_url,
        "grocy_api_key": settings.grocy_api_key,
        "llm_api_url": settings.llm_api_url,
        "llm_api_key": settings.llm_api_key,
        "llm_model": settings.llm_model,
        "max_recipe_history": settings.max_recipe_history,
        "apprise_url": settings.apprise_url,
        "database_path": settings.database_path,
        "recipe_export_path": settings.recipe_export_path,
    }
    
    # Get overrides from database
    db_settings = await db.get_all_settings()
    
    # Map database keys to config keys
    # We use specific keys in the DB for these overrides
    mapping = {
        "GROCY_URL": "grocy_url",
        "GROCY_API_KEY": "grocy_api_key",
        "LLM_API_URL": "llm_api_url",
        "LLM_API_KEY": "llm_api_key",
        "LLM_MODEL": "llm_model",
        "MAX_RECIPE_HISTORY": "max_recipe_history",
        "APPRISE_URL": "apprise_url"
    }
    
    for db_key, config_key in mapping.items():
        if db_key in db_settings:
            value = db_settings[db_key]
            # Convert types if necessary
            if config_key == "max_recipe_history":
                try:
                    value = int(value)
                except ValueError:
                    continue
            config[config_key] = value
            
    return config

