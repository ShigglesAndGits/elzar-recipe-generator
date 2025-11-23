from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Grocy Configuration
    grocy_url: str = "https://groceries.bironfamily.net"
    grocy_api_key: str = ""
    
    # LLM Configuration
    llm_api_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    llm_model: str = "google/gemini-2.0-flash-exp:free"
    
    # Application Settings
    max_recipe_history: int = 1000
    database_path: str = "../data/recipes.db"
    recipe_export_path: str = "../data/recipes"
    
    # Notification
    apprise_url: Optional[str] = None
    
    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

