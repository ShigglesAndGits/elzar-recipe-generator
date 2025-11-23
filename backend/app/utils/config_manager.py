from ..config import settings

async def get_effective_config():
    """
    Get the effective configuration from .env file.
    Settings are now managed directly in the .env file.
    """
    # Return settings as dict - no database override needed
    config = {
        "grocy_url": settings.grocy_url,
        "grocy_api_key": settings.grocy_api_key,
        "llm_api_url": settings.llm_api_url,
        "llm_api_key": settings.llm_api_key,
        "llm_model": settings.llm_model,
        "max_recipe_history": settings.max_recipe_history,
        "apprise_url": settings.apprise_url or "",
        "database_path": settings.database_path,
        "recipe_export_path": settings.recipe_export_path,
        "backend_host": settings.backend_host,
        "backend_port": settings.backend_port,
        "unit_preference": settings.unit_preference,
    }
            
    return config

