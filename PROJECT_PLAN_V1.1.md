# Elzar v1.1 - Inventory Management & Recipe Integration 🌶️

## Overview
Version 1.1 adds intelligent inventory management features using LLM-powered item matching to bridge the gap between real-world food lists (receipts, recipes, shopping lists) and Grocy's inventory system.

## Feature Set

### 1. Bulk Inventory Manager (New Page)
**Purpose:** Parse and process lists of food items from various sources

**User Flow:**
1. User pastes text (Instacart receipt, recipe ingredient list, etc.)
2. Click "Parse with LLM" button
3. LLM extracts items and attempts to match with existing Grocy products
4. Review table shows:
   - Original text (what was found)
   - Parsed item name
   - Quantity (editable)
   - Unit (editable)
   - Matched Grocy product (dropdown to change)
   - Confidence (High/Medium/Low/NEW)
   - Action buttons (Purchase/Consume/Skip) per item
5. Bulk action buttons at bottom (Purchase All / Consume All / Skip All)
6. Confirmation modal shows what will be created/updated
7. Execute actions

### 2. Recipe Integration Features (On Recipe Display Page)
Add three new buttons to the recipe display:

#### A. **Consume Recipe Ingredients**
- Parse the generated recipe's ingredient list
- Match ingredients to Grocy inventory
- Show confirmation dialog with matched items
- Consume from stock when confirmed

#### B. **Add Missing Ingredients to Shopping List**
- Identify ingredients not in stock or insufficient quantity
- Add to Grocy shopping list
- Show confirmation of what was added

#### C. **Save Recipe to Grocy**
- Create a recipe entity in Grocy
- Link ingredients with quantities
- Store instructions and metadata

## Grocy API Research Summary

Based on the existing `grocy_client.py` and Grocy API patterns, here are the key endpoints we need:

### Stock Management Endpoints

```python
# Get all products (for matching)
GET /api/objects/products
Response: [{"id": 1, "name": "Milk", ...}, ...]

# Get current stock
GET /api/stock
Response: [{"product_id": 1, "amount": 2.5, ...}, ...]

# Purchase/Add stock
POST /api/stock/products/{product_id}/add
Body: {
    "amount": 1.0,
    "best_before_date": "2025-12-31",  # Optional
    "price": 3.99,  # Optional
    "location_id": 1,  # Optional
    "shopping_location_id": 1  # Optional
}

# Consume stock
POST /api/stock/products/{product_id}/consume
Body: {
    "amount": 1.0,
    "spoiled": false,  # Optional
    "transaction_type": "consume"  # or "opened"
}

# Create new product
POST /api/objects/products
Body: {
    "name": "New Product Name",
    "description": "",
    "location_id": 1,  # Default location
    "qu_id_purchase": 1,  # Quantity unit for purchase
    "qu_id_stock": 1,  # Quantity unit for stock
    "qu_factor_purchase_to_stock": 1
}
```

### Shopping List Endpoints

```python
# Add to shopping list
POST /api/stock/shoppinglist/add-product
Body: {
    "product_id": 1,
    "list_id": 1,  # Optional, default list
    "product_amount": 1,
    "note": ""  # Optional
}

# Get shopping lists
GET /api/objects/shopping_lists
```

### Recipe Endpoints

```python
# Create recipe
POST /api/objects/recipes
Body: {
    "name": "Recipe Name",
    "description": "Full recipe text",
    "base_servings": 4,
    "desired_servings": 4,
    "type": "normal"  # or "mealplan"
}

# Add ingredient to recipe
POST /api/objects/recipes_pos
Body: {
    "recipe_id": 1,
    "product_id": 1,
    "amount": 2.0,
    "qu_id": 1,  # Quantity unit
    "note": "",
    "variable_amount": "",
    "only_check_single_unit_in_stock": 0
}
```

## Technical Architecture

### Backend Changes

#### 1. New Router: `backend/app/routers/inventory.py`

```python
@router.post("/api/inventory/parse")
async def parse_inventory_text(text: str, action_type: str):
    """
    Parse text and match to Grocy products using LLM
    Returns: List of ParsedItem objects
    """

@router.post("/api/inventory/purchase")
async def purchase_items(items: List[InventoryItem]):
    """
    Purchase/add multiple items to Grocy stock
    """

@router.post("/api/inventory/consume")
async def consume_items(items: List[InventoryItem]):
    """
    Consume multiple items from Grocy stock
    """

@router.post("/api/inventory/create-products")
async def create_products(products: List[ProductCreate]):
    """
    Create new products in Grocy
    """
```

#### 2. Enhanced `backend/app/services/grocy_client.py`

Add implementations for:
- `purchase_product(product_id, amount, best_before_date=None, price=None)`
- `consume_product(product_id, amount, spoiled=False)`
- `create_product(name, description="", location_id=None, qu_id=None)`
- `add_to_shopping_list(product_id, amount, list_id=None, note="")`
- `create_recipe(name, description, base_servings, ingredients)`
- `get_all_products()` (already exists)
- `get_quantity_units()` - Get available units
- `get_locations()` - Get storage locations

#### 3. New LLM Service: `backend/app/services/inventory_matcher.py`

```python
class InventoryMatcher:
    """
    Uses LLM to parse text and match items to Grocy products
    """
    
    async def parse_and_match(
        self,
        input_text: str,
        grocy_products: List[Dict],
        action_type: str  # "purchase" or "consume"
    ) -> List[ParsedItem]:
        """
        Parse text and match to existing products
        Returns list with confidence scores
        """
    
    async def extract_recipe_ingredients(
        self,
        recipe_text: str,
        grocy_products: List[Dict]
    ) -> List[RecipeIngredient]:
        """
        Extract ingredients from recipe text and match to products
        """
```

#### 4. New Models in `backend/app/models.py`

```python
class ParsedItem(BaseModel):
    original_text: str
    item_name: str
    quantity: float
    unit: str
    matched_product_id: Optional[int]
    matched_product_name: Optional[str]
    confidence: str  # "high", "medium", "low", "new"
    suggested_create: bool

class InventoryItem(BaseModel):
    product_id: Optional[int]
    product_name: str
    quantity: float
    unit: str
    action: str  # "purchase", "consume", "skip"
    create_if_missing: bool = False
    best_before_date: Optional[str] = None
    price: Optional[float] = None

class RecipeIngredient(BaseModel):
    ingredient_text: str
    product_id: Optional[int]
    product_name: str
    quantity: float
    unit: str
    confidence: str
    in_stock: bool
    stock_amount: Optional[float] = None

class RecipeSaveRequest(BaseModel):
    recipe_id: int  # Our internal recipe ID
    recipe_name: str
    servings: int
    ingredients: List[RecipeIngredient]
```

### Frontend Changes

#### 1. New Page: `frontend/src/pages/InventoryManager.jsx`

**Components:**
- Text area for pasting input
- "Parse with LLM" button
- Loading state during parsing
- Results table with:
  - Original text column
  - Item name (editable)
  - Quantity (editable input)
  - Unit (dropdown)
  - Matched product (searchable dropdown)
  - Confidence badge (color-coded)
  - Action buttons per row (Purchase/Consume/Skip)
- Bulk action buttons at bottom
- Confirmation modal before executing

#### 2. Enhanced `frontend/src/pages/Generator.jsx`

Add three new buttons to the recipe display section:

```jsx
{!loading && currentRecipe && (
  <div className="recipe-actions mt-4 space-y-2">
    <button onClick={handleConsumeIngredients}>
      🍽️ Consume Recipe Ingredients
    </button>
    <button onClick={handleAddMissingToShoppingList}>
      🛒 Add Missing to Shopping List
    </button>
    <button onClick={handleSaveRecipeToGrocy}>
      💾 Save Recipe to Grocy
    </button>
  </div>
)}
```

#### 3. New Components

- `frontend/src/components/InventoryTable.jsx` - Reusable table for parsed items
- `frontend/src/components/ProductMatcher.jsx` - Dropdown for product matching
- `frontend/src/components/ConfirmationModal.jsx` - Show what will be created/updated

#### 4. Update Navigation

Add "Inventory Manager" to the nav bar

### LLM Prompts

#### Inventory Parsing Prompt

```
You are a grocery inventory assistant. Parse the following text and extract all food items with their quantities.

INPUT TEXT:
{user_pasted_text}

AVAILABLE GROCY PRODUCTS:
{json_list_of_products}

For each food item you find:
1. Extract the item name (normalized, e.g., "2% milk" -> "Milk")
2. Extract quantity as a number
3. Extract or infer the unit (g, kg, ml, l, count, etc.)
4. Match to the best Grocy product from the list above
5. Assign confidence: "high" (exact match), "medium" (close match), "low" (uncertain), "new" (no match found)

Return ONLY valid JSON array:
[
  {
    "original_text": "1gal 2% milk",
    "item_name": "Milk",
    "quantity": 3.78,
    "unit": "l",
    "matched_product_id": 5,
    "matched_product_name": "Milk",
    "confidence": "high"
  },
  ...
]

Rules:
- Convert units to metric when possible (gallons -> liters, oz -> grams)
- If no match found, set matched_product_id to null and confidence to "new"
- Ignore non-food items
- Combine duplicate items
```

#### Recipe Ingredient Extraction Prompt

```
You are a recipe analysis assistant. Extract all ingredients from this recipe and match them to Grocy products.

RECIPE TEXT:
{recipe_text}

AVAILABLE GROCY PRODUCTS:
{json_list_of_products}

CURRENT STOCK LEVELS:
{json_stock_info}

For each ingredient:
1. Extract ingredient name
2. Extract quantity
3. Extract unit
4. Match to Grocy product
5. Check if in stock and sufficient quantity
6. Assign confidence

Return ONLY valid JSON array:
[
  {
    "ingredient_text": "2 cups all-purpose flour",
    "product_id": 12,
    "product_name": "Flour",
    "quantity": 250,
    "unit": "g",
    "confidence": "high",
    "in_stock": true,
    "stock_amount": 1000
  },
  ...
]
```

## Configuration Updates

### New Settings
Add to Settings page:
- **Preferred Units**: Radio buttons for "Metric" or "Imperial"
  - Stored in database settings table
  - Passed to LLM for intelligent unit conversion
  - Default: Metric

### LLM Model
- Use existing global LLM model setting from Settings page
- Future enhancement: Per-task model selection

### Testing Environment
- Use production Grocy instance: `https://groceries.bironfamily.net`
- Instance is mostly empty, perfect for testing
- Will use real sample data provided by user

## Implementation Plan

### Phase 1: Backend Foundation (Days 1-2)
- [ ] Implement Grocy API methods in `grocy_client.py`
  - [ ] `purchase_product()`
  - [ ] `consume_product()`
  - [ ] `create_product()`
  - [ ] `add_to_shopping_list()`
  - [ ] `create_recipe()` and `add_recipe_ingredient()`
  - [ ] `get_quantity_units()`
  - [ ] `get_locations()`
- [ ] Test all Grocy endpoints manually with curl/Postman
- [ ] Add new models to `models.py`

### Phase 2: LLM Matching Service (Days 2-3)
- [ ] Create `inventory_matcher.py`
- [ ] Implement `parse_and_match()` method
- [ ] Implement `extract_recipe_ingredients()` method
- [ ] Test LLM parsing with various inputs
- [ ] Fine-tune prompts for accuracy

### Phase 3: Inventory Router (Days 3-4)
- [ ] Create `inventory.py` router
- [ ] Implement `/api/inventory/parse` endpoint
- [ ] Implement `/api/inventory/purchase` endpoint
- [ ] Implement `/api/inventory/consume` endpoint
- [ ] Implement `/api/inventory/create-products` endpoint
- [ ] Add error handling and validation

### Phase 4: Recipe Integration Endpoints (Days 4-5)
- [ ] Add `/api/recipes/{id}/consume-ingredients` endpoint
- [ ] Add `/api/recipes/{id}/add-missing-to-shopping-list` endpoint
- [ ] Add `/api/recipes/{id}/save-to-grocy` endpoint
- [ ] Test with real recipes

### Phase 5: Frontend - Inventory Manager Page (Days 5-7)
- [ ] Create `InventoryManager.jsx` page
- [ ] Add text area and parse button
- [ ] Create `InventoryTable.jsx` component
- [ ] Create `ProductMatcher.jsx` dropdown component
- [ ] Implement per-item action buttons
- [ ] Implement bulk action buttons
- [ ] Create `ConfirmationModal.jsx`
- [ ] Add to navigation

### Phase 6: Frontend - Recipe Integration (Days 7-8)
- [ ] Add three action buttons to `Generator.jsx`
- [ ] Implement `handleConsumeIngredients()`
- [ ] Implement `handleAddMissingToShoppingList()`
- [ ] Implement `handleSaveRecipeToGrocy()`
- [ ] Add confirmation modals for each action
- [ ] Show success/error toasts

### Phase 7: Testing & Polish (Days 8-9)
- [ ] Test with real Instacart receipts
- [ ] Test with recipe ingredient lists
- [ ] Test edge cases (typos, abbreviations, unknown items)
- [ ] Improve LLM prompts based on results
- [ ] Add loading states and error handling
- [ ] Mobile responsiveness testing

### Phase 8: Documentation (Day 9)
- [ ] Update README with new features
- [ ] Document API endpoints
- [ ] Add usage examples
- [ ] Update PROJECT_PLAN.md

## Edge Cases & Considerations

### Matching Challenges
- **Ambiguous items**: "Tomatoes" could be fresh, canned, cherry, etc.
  - Solution: Show multiple matches, let user pick
- **Unit conversions**: Gallons to liters, oz to grams
  - Solution: LLM handles conversion, provide unit dropdown for manual override
- **Typos**: "org bnnas" = "organic bananas"
  - Solution: LLM fuzzy matching, confidence scores
- **Non-food items**: Receipts include paper towels, etc.
  - Solution: LLM filters non-food, user can manually skip

### Grocy Integration
- **Product creation**: What location? What quantity unit?
  - Solution: LLM fetches all locations from Grocy and intelligently chooses (Pantry vs Fridge), infer unit from parsed text
- **Stock locations**: Multiple storage locations
  - Solution: LLM-powered smart location selection based on product type
- **Price tracking**: Should we store prices from receipts?
  - Solution: Yes, optional field, useful for budgeting
- **Unit preferences**: Metric vs Imperial
  - Solution: Add setting in Settings page, pass to LLM for unit conversion

### User Experience
- **Large lists**: 50+ items from big shopping trip
  - Solution: Pagination, bulk actions, "Accept all high-confidence matches"
- **Undo**: Accidentally consumed wrong items
  - Solution: Show transaction history, add "Undo last action" button (future)
- **Partial matches**: Only some ingredients in stock
  - Solution: Clearly show what's missing, offer to add to shopping list

## Success Criteria

v1.1 is complete when:
1. ✅ User can paste an Instacart receipt and bulk-purchase items
2. ✅ User can paste a recipe and bulk-consume ingredients
3. ✅ LLM successfully matches items with >80% accuracy on high-confidence matches
4. ✅ User can review and edit matches before committing
5. ✅ "Consume Recipe Ingredients" button works on generated recipes
6. ✅ "Add Missing to Shopping List" button works on generated recipes
7. ✅ "Save Recipe to Grocy" button creates recipe entity in Grocy
8. ✅ All actions show clear confirmation dialogs
9. ✅ Error handling for Grocy API failures
10. ✅ Mobile-responsive UI

## Future Enhancements (v1.2+)

- Barcode scanning integration
- Photo OCR for paper receipts
- Automatic price tracking and budgeting
- Transaction history and undo functionality
- Smart expiration date estimation
- Batch recipe meal planning (consume for whole week)
- Integration with meal planning calendar

---

*BAM! Let's manage that inventory! 🌶️*

