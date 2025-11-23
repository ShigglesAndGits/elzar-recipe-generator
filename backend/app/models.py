from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Request Models
class RecipeGenerationRequest(BaseModel):
    """Request model for recipe generation"""
    cuisine: Optional[str] = "No Preference"
    active_profiles: List[str] = Field(default_factory=list)
    prioritize_expiring: bool = False
    time_minutes: int = Field(default=60, ge=15, le=180)
    effort_level: str = "Medium"  # Low, Medium, High
    dish_preference: str = "I don't care"  # No dishes, Few dishes, I don't care
    calories_per_serving: Optional[int] = None
    use_external_ingredients: bool = False
    elzar_voice: bool = True
    servings: str = "3-4"  # 1-2, 3-4, 5-6, 7+
    high_leftover_potential: bool = False
    user_prompt: Optional[str] = None  # Additional user notes


class RecipeResponse(BaseModel):
    """Response model for generated recipe"""
    id: int
    recipe_text: str
    cuisine: Optional[str] = None
    time_minutes: Optional[int] = None
    effort_level: Optional[str] = None
    dish_preference: Optional[str] = None
    calories_per_serving: Optional[int] = None
    used_external_ingredients: bool
    prioritize_expiring: bool
    active_profiles: Optional[str] = None  # JSON string
    created_at: datetime
    llm_model: Optional[str] = None


class RecipeFilter(BaseModel):
    """Filter model for recipe history"""
    cuisine: Optional[str] = None
    min_time: Optional[int] = None
    max_time: Optional[int] = None
    effort_level: Optional[str] = None
    min_calories: Optional[int] = None
    max_calories: Optional[int] = None
    profile_name: Optional[str] = None
    search_text: Optional[str] = None


# Dietary Profile Models
class DietaryProfileCreate(BaseModel):
    """Model for creating a new dietary profile"""
    name: str = Field(..., min_length=1, max_length=100)
    dietary_restrictions: str = Field(..., min_length=1)


class DietaryProfileUpdate(BaseModel):
    """Model for updating a dietary profile"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    dietary_restrictions: Optional[str] = Field(None, min_length=1)


class DietaryProfileResponse(BaseModel):
    """Response model for dietary profile"""
    id: int
    name: str
    dietary_restrictions: str
    created_at: datetime
    updated_at: datetime


# Settings Models
class SettingUpdate(BaseModel):
    """Model for updating a setting"""
    key: str
    value: str


class SettingResponse(BaseModel):
    """Response model for settings"""
    key: str
    value: str
    updated_at: datetime


# Notification Models
class NotificationRequest(BaseModel):
    """Request model for sending notifications"""
    recipe_id: int
    title: Optional[str] = "Recipe from Elzar"


# Inventory Management Models (v1.1)
class ParsedItem(BaseModel):
    """Parsed item from text input with Grocy product matching"""
    original_text: str
    item_name: str
    quantity: float
    unit: str
    grocy_product_id: Optional[int] = None
    grocy_product_name: Optional[str] = None
    confidence: str  # "high", "medium", "low", "new"
    location_id: Optional[int] = None
    quantity_unit_id: Optional[int] = None


class InventoryParseRequest(BaseModel):
    """Request to parse inventory text"""
    text: str
    action_type: str  # "purchase" or "consume"


class InventoryItem(BaseModel):
    """Item for inventory transaction"""
    product_id: Optional[int] = None
    product_name: str
    amount: float  # Using 'amount' to match Grocy API and frontend
    unit: str
    action: str  # "purchase", "consume", "skip"
    create_if_missing: bool = False
    location_id: Optional[int] = None
    quantity_unit_id: Optional[int] = None
    best_before_date: Optional[str] = None
    price: Optional[float] = None


class InventoryActionRequest(BaseModel):
    """Request to perform inventory actions"""
    items: List[InventoryItem]


class ProductCreateRequest(BaseModel):
    """Request to create new products"""
    name: str
    location_id: int
    qu_id_stock: int
    description: str = ""


class RecipeIngredient(BaseModel):
    """Ingredient extracted from recipe with Grocy matching"""
    ingredient_text: str
    product_id: Optional[int] = None
    product_name: str
    quantity: float
    unit: str
    confidence: str  # "high", "medium", "low", "new"
    in_stock: bool
    stock_amount: Optional[float] = None
    qu_id: Optional[int] = None  # Quantity unit ID


class RecipeConsumeRequest(BaseModel):
    """Request to consume recipe ingredients"""
    recipe_id: int  # Our internal recipe ID
    ingredients: List[RecipeIngredient]


class RecipeShoppingListRequest(BaseModel):
    """Request to add missing ingredients to shopping list"""
    recipe_id: int
    ingredients: List[RecipeIngredient]


class RecipeSaveRequest(BaseModel):
    """Request to save recipe to Grocy"""
    recipe_id: int  # Our internal recipe ID
    recipe_name: str
    servings: int
    recipe_text: str
    ingredients: List[RecipeIngredient]

