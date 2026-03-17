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
    llm_max_tokens: int = 16000  # Max output tokens for LLM responses

    # Vision Model Configuration (for pantry scanning)
    vision_api_url: Optional[str] = None  # Falls back to llm_api_url if not set
    vision_api_key: Optional[str] = None  # Falls back to llm_api_key if not set
    vision_model: Optional[str] = None  # Falls back to llm_model if not set
    
    # Application Settings
    max_recipe_history: int = 1000
    database_path: str = "../data/recipes.db"
    recipe_export_path: str = "../data/recipes"
    unit_preference: str = "metric"  # "metric" or "imperial"
    
    # Notification
    apprise_url: Optional[str] = None
    
    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8001
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

