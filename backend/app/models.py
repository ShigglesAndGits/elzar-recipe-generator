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
    servings: str = "3-4"  # 1-2, 3-4, 5-6, 7+, 8+ (bulk)
    bulk_prep: bool = False  # Bulk prep mode for freezer-friendly meals
    high_leftover_potential: bool = False
    available_equipment: List[str] = Field(default_factory=list)  # Kitchen equipment available
    user_prompt: Optional[str] = None  # Additional user notes


class AdviceRequest(BaseModel):
    """Request model for cooking advice"""
    question: str = Field(..., min_length=1, max_length=1000)
    active_profiles: List[str] = Field(default_factory=list)
    elzar_voice: bool = False
    include_inventory: bool = True  # Whether to include inventory context


class AdviceResponse(BaseModel):
    """Response model for cooking advice"""
    question: str
    advice: str
    llm_model: str


class RecipeResponse(BaseModel):
    """Response model for generated recipe"""
    id: int
    recipe_text: str
    cuisine: Optional[str] = None
    time_minutes: Optional[int] = None
    effort_level: Optional[str] = None
    dish_preference: Optional[str] = None
    calories_per_serving: Optional[int] = None
    estimated_cost: Optional[float] = None  # Estimated total cost in USD
    used_external_ingredients: bool
    prioritize_expiring: bool
    active_profiles: Optional[str] = None  # JSON string
    created_at: datetime
    llm_model: Optional[str] = None
    is_locked: bool = False
    is_saved: bool = False
    tags: Optional[str] = "[]"  # JSON string
    parent_recipe_id: Optional[int] = None


class ManualRecipeCreate(BaseModel):
    """Request model for manually creating a recipe"""
    recipe_text: str = Field(..., min_length=1)
    cuisine: Optional[str] = None
    time_minutes: Optional[int] = Field(None, ge=1, le=1440)
    effort_level: Optional[str] = None
    calories_per_serving: Optional[int] = Field(None, ge=1)
    is_locked: bool = False
    is_saved: bool = False


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


# Ideas Models
class IdeaCreate(BaseModel):
    """Request model for creating an idea"""
    name: str = Field(..., min_length=1, max_length=200)
    notes: str = ""
    tags: List[str] = Field(default_factory=list)
    calorie_estimate: Optional[str] = None  # e.g. "300-400" or "~500"
    status: str = "idea"  # idea, planned, tested, favorite


class IdeaUpdate(BaseModel):
    """Request model for updating an idea"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    calorie_estimate: Optional[str] = None
    status: Optional[str] = None


class IdeaResponse(BaseModel):
    """Response model for an idea"""
    id: int
    name: str
    notes: str
    tags: List[str] = Field(default_factory=list)
    calorie_estimate: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


# User Preferences Models
class UserPreferencesUpdate(BaseModel):
    """Model for updating user preferences"""
    content: str = Field(..., max_length=8000)


class UserPreferencesResponse(BaseModel):
    """Response model for user preferences"""
    content: str
    updated_at: Optional[datetime] = None


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


# Meal Planning Models (v1.2)
class MealPlanRequest(BaseModel):
    """Request model for meal plan generation"""
    days: int = Field(default=7, ge=1, le=14)
    people: int = Field(default=2, ge=1, le=12)

    # Meal toggles
    generate_breakfast: bool = True
    generate_lunch: bool = True
    generate_dinner: bool = True
    generate_snacks: bool = False

    # Budget level
    budget_level: str = "moderate"  # "broke", "dirt_cheap", "cheap", "moderate", "high", "luxury"

    # Daily calorie target (meals should help achieve this, not necessarily add up to it)
    daily_calorie_target: Optional[int] = None

    # Effort levels for each meal type (1-5: 1=pre-packaged, 5=high effort)
    breakfast_effort: int = Field(default=2, ge=1, le=5)
    lunch_effort: int = Field(default=2, ge=1, le=5)
    dinner_effort: int = Field(default=3, ge=1, le=5)
    snack_effort: int = Field(default=1, ge=1, le=5)

    # Variety level (1=minimal variety/reuse ingredients, 5=maximum variety)
    variety_level: int = Field(default=3, ge=1, le=5)

    # Profile/dietary restrictions
    active_profiles: List[str] = Field(default_factory=list)

    # Use ingredients from Grocy inventory
    use_inventory: bool = True
    prioritize_expiring: bool = False

    # Additional notes
    user_prompt: Optional[str] = None


class MealPlanRecipe(BaseModel):
    """A single recipe within a meal plan"""
    id: str  # Unique ID within the meal plan (e.g., "day1_dinner")
    day: int  # Day number (1-14)
    meal_type: str  # "breakfast", "lunch", "dinner", "snack"
    title: str
    recipe_text: str
    calories_estimate: Optional[int] = None
    prep_time_minutes: Optional[int] = None
    servings: int = 2
    estimated_cost: Optional[float] = None  # Estimated cost in USD


class MealPlanResponse(BaseModel):
    """Response model for generated meal plan"""
    id: int
    overview: str  # Summary/intro text
    recipes: List[MealPlanRecipe]
    total_days: int
    total_people: int
    budget_level: str
    estimated_total_cost: Optional[float] = None  # Sum of all recipe costs
    created_at: datetime
    llm_model: Optional[str] = None


class MealPlanSummary(BaseModel):
    """Summary for meal plan history"""
    id: int
    total_days: int
    total_people: int
    budget_level: str
    meal_count: int
    estimated_total_cost: Optional[float] = None  # Sum of all recipe costs
    created_at: datetime

