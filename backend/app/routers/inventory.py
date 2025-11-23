from fastapi import APIRouter, HTTPException, status
from typing import List
import json

from ..models import (
    InventoryParseRequest,
    ParsedItem,
    InventoryActionRequest,
    InventoryItem,
    ProductCreateRequest
)
from ..services.grocy_client import GrocyClient
from ..services.inventory_matcher import InventoryMatcher
from ..utils.config_manager import get_effective_config

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.post("/parse", response_model=List[ParsedItem])
async def parse_inventory_text(request: InventoryParseRequest):
    """
    Parse text input and match items to Grocy products using LLM
    
    This endpoint:
    1. Fetches all Grocy products and locations
    2. Uses LLM to parse the input text
    3. Matches items to existing products
    4. Suggests storage locations
    5. Returns confidence scores
    """
    config = await get_effective_config()
    
    # Initialize clients
    grocy_client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
    matcher = InventoryMatcher(
        config["llm_api_url"],
        config["llm_api_key"],
        config["llm_model"]
    )
    
    try:
        # Fetch Grocy data
        products = await grocy_client.get_products()
        locations = await grocy_client.get_locations()
        
        # Get unit preference from settings (default to metric)
        unit_preference = config.get("unit_preference", "metric")
        
        # Parse and match using LLM
        parsed_items = await matcher.parse_and_match(
            request.text,
            products,
            locations,
            unit_preference
        )
        
        # Convert to ParsedItem models
        result = [ParsedItem(**item) for item in parsed_items]
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing inventory: {str(e)}"
        )


@router.post("/purchase")
async def purchase_items(request: InventoryActionRequest):
    """
    Purchase/add multiple items to Grocy stock
    
    This endpoint:
    1. Creates new products if needed (when create_if_missing=True)
    2. Adds stock for each item
    3. Returns summary of actions taken
    """
    config = await get_effective_config()
    grocy_client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
    
    results = {
        "success": [],
        "failed": [],
        "created_products": []
    }
    
    try:
        # Get quantity units for product creation
        quantity_units = await grocy_client.get_quantity_units()
        
        # Create a unit lookup (name -> id)
        unit_lookup = {qu["name"].lower(): qu["id"] for qu in quantity_units}
        # Add common aliases
        unit_lookup.update({
            "count": unit_lookup.get("piece", unit_lookup.get("pcs", 2)),  # Default to Piece
            "g": unit_lookup.get("gram", unit_lookup.get("g", 2)),
            "kg": unit_lookup.get("kilogram", unit_lookup.get("kg", 2)),
            "ml": unit_lookup.get("milliliter", unit_lookup.get("ml", 2)),
            "l": unit_lookup.get("liter", unit_lookup.get("l", 2)),
            "oz": unit_lookup.get("ounce", unit_lookup.get("oz", 2)),
            "lb": unit_lookup.get("pound", unit_lookup.get("lb", 2)),
            "gal": unit_lookup.get("gallon", unit_lookup.get("gal", 2)),
        })
        
        # Common units to auto-create if missing
        common_units = {
            "gram": "grams",
            "kilogram": "kilograms",
            "ounce": "ounces",
            "pound": "pounds",
            "liter": "liters",
            "milliliter": "milliliters",
            "gallon": "gallons",
            "cup": "cups",
            "tablespoon": "tablespoons",
            "teaspoon": "teaspoons",
        }
        
        for item in request.items:
            if item.action != "purchase":
                continue
            
            try:
                # Create product if needed
                if item.create_if_missing and item.product_id is None:
                    # Get or create unit ID
                    unit_name_lower = item.unit.lower()
                    qu_id = unit_lookup.get(unit_name_lower)
                    
                    # If unit doesn't exist, try to create it
                    if not qu_id and unit_name_lower in common_units:
                        try:
                            new_unit = await grocy_client.create_quantity_unit(
                                name=unit_name_lower.capitalize(),
                                name_plural=common_units[unit_name_lower]
                            )
                            qu_id = new_unit["created_object_id"]
                            unit_lookup[unit_name_lower] = qu_id
                            print(f"✅ Created quantity unit: {unit_name_lower} (ID: {qu_id})")
                        except Exception as e:
                            # Unit might already exist, try to fetch it again
                            if "constraint" in str(e).lower() or "unique" in str(e).lower():
                                print(f"ℹ️ Unit '{unit_name_lower}' already exists, fetching...")
                                existing_units = await grocy_client.get_quantity_units()
                                unit_lookup = {u["name"].lower(): u["id"] for u in existing_units}
                                qu_id = unit_lookup.get(unit_name_lower)
                                if not qu_id:
                                    print(f"⚠️ Failed to find unit '{unit_name_lower}' after refresh: {e}")
                                    qu_id = 2  # Fallback to Piece
                            else:
                                print(f"⚠️ Failed to create unit '{unit_name_lower}': {e}")
                                qu_id = 2  # Fallback to Piece
                    elif not qu_id:
                        qu_id = 2  # Default to Piece if not a common unit
                    
                    # Create product
                    created = await grocy_client.create_product(
                        name=item.product_name,
                        location_id=item.location_id or 1,  # Default location
                        qu_id_stock=qu_id,
                        description=f"Auto-created from inventory import"
                    )
                    
                    item.product_id = created["created_object_id"]
                    results["created_products"].append({
                        "name": item.product_name,
                        "id": item.product_id
                    })
                
                # Purchase the product
                if item.product_id:
                    await grocy_client.purchase_product(
                        product_id=item.product_id,
                        amount=item.amount,
                        best_before_date=item.best_before_date,
                        price=item.price,
                        location_id=item.location_id
                    )
                    
                    results["success"].append({
                        "product_id": item.product_id,
                        "product_name": item.product_name,
                        "quantity": item.amount,
                        "unit": item.unit
                    })
                else:
                    results["failed"].append({
                        "product_name": item.product_name,
                        "reason": "No product ID and create_if_missing=False"
                    })
                    
            except Exception as e:
                results["failed"].append({
                    "product_name": item.product_name,
                    "reason": str(e)
                })
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error purchasing items: {str(e)}"
        )


@router.post("/consume")
async def consume_items(request: InventoryActionRequest):
    """
    Consume/remove multiple items from Grocy stock
    
    This endpoint:
    1. Consumes stock for each item
    2. Skips items that don't have a product_id
    3. Returns summary of actions taken
    """
    config = await get_effective_config()
    grocy_client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
    
    results = {
        "success": [],
        "failed": []
    }
    
    try:
        for item in request.items:
            if item.action != "consume":
                continue
            
            try:
                if item.product_id:
                    await grocy_client.consume_product(
                        product_id=item.product_id,
                        amount=item.amount,
                        spoiled=False,
                        location_id=item.location_id
                    )
                    
                    results["success"].append({
                        "product_id": item.product_id,
                        "product_name": item.product_name,
                        "quantity": item.amount,
                        "unit": item.unit
                    })
                else:
                    results["failed"].append({
                        "product_name": item.product_name,
                        "reason": "No product ID - cannot consume"
                    })
                    
            except Exception as e:
                results["failed"].append({
                    "product_name": item.product_name,
                    "reason": str(e)
                })
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error consuming items: {str(e)}"
        )


@router.post("/add-to-shopping-list")
async def add_to_shopping_list(request: InventoryActionRequest):
    """
    Add items to Grocy shopping list
    
    This endpoint:
    1. Creates missing products if requested
    2. Adds items to the shopping list
    """
    config = await get_effective_config()
    grocy_client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
    
    results = {
        "success": [],
        "failed": [],
        "created_products": []
    }
    
    try:
        # Get existing units for auto-creation
        existing_units = await grocy_client.get_quantity_units()
        unit_name_to_id = {u["name"].lower(): u["id"] for u in existing_units}
        
        # Get locations for auto-creation
        locations = await grocy_client.get_locations()
        location_id = locations[0]["id"] if locations else 1  # Default to first location
        
        for item in request.items:
            try:
                product_id = item.product_id
                
                # Create product if needed
                if item.create_if_missing and not product_id:
                    # Get or create unit
                    unit_lower = item.unit.lower() if item.unit else "unit"
                    qu_id = unit_name_to_id.get(unit_lower)
                    
                    if not qu_id:
                        # Try to create common units
                        common_units = {
                            "g": ("Gram", "Grams"),
                            "gram": ("Gram", "Grams"),
                            "kg": ("Kilogram", "Kilograms"),
                            "kilogram": ("Kilogram", "Kilograms"),
                            "oz": ("Ounce", "Ounces"),
                            "ounce": ("Ounce", "Ounces"),
                            "lb": ("Pound", "Pounds"),
                            "pound": ("Pound", "Pounds"),
                            "ml": ("Milliliter", "Milliliters"),
                            "l": ("Liter", "Liters"),
                            "liter": ("Liter", "Liters"),
                            "fl oz": ("Fluid Ounce", "Fluid Ounces"),
                            "pt": ("Pint", "Pints"),
                            "qt": ("Quart", "Quarts"),
                            "gal": ("Gallon", "Gallons"),
                        }
                        
                        if unit_lower in common_units:
                            name, plural = common_units[unit_lower]
                            try:
                                created_unit = await grocy_client.create_quantity_unit(name, plural, unit_lower)
                                qu_id = created_unit["created_object_id"]
                                unit_name_to_id[unit_lower] = qu_id
                            except Exception as unit_error:
                                # Unit might already exist, try to fetch it again
                                if "constraint" in str(unit_error).lower() or "unique" in str(unit_error).lower():
                                    existing_units = await grocy_client.get_quantity_units()
                                    unit_name_to_id = {u["name"].lower(): u["id"] for u in existing_units}
                                    qu_id = unit_name_to_id.get(unit_lower) or unit_name_to_id.get(name.lower())
                                    if not qu_id:
                                        raise unit_error
                                else:
                                    raise unit_error
                        else:
                            qu_id = unit_name_to_id.get("unit", 1)
                    
                    # Create product
                    created_product = await grocy_client.create_product(
                        name=item.product_name,
                        location_id=item.location_id or location_id,
                        qu_id_stock=qu_id
                    )
                    product_id = created_product["created_object_id"]
                    results["created_products"].append({
                        "name": item.product_name,
                        "id": product_id
                    })
                
                if not product_id:
                    results["failed"].append({
                        "item": item.product_name,
                        "reason": "No product ID and creation not enabled"
                    })
                    continue
                
                # Add to shopping list
                await grocy_client.add_to_shopping_list(
                    product_id=product_id,
                    amount=item.amount,
                    shopping_list_id=1  # Default shopping list
                )
                
                results["success"].append({
                    "item": item.product_name,
                    "amount": item.amount,
                    "unit": item.unit
                })
                
            except Exception as e:
                results["failed"].append({
                    "item": item.product_name if hasattr(item, 'product_name') else "Unknown",
                    "reason": str(e)
                })
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding to shopping list: {str(e)}"
        )


@router.post("/create-products")
async def create_products(products: List[ProductCreateRequest]):
    """
    Create multiple new products in Grocy
    
    Returns list of created product IDs
    """
    config = await get_effective_config()
    grocy_client = GrocyClient(config["grocy_url"], config["grocy_api_key"])
    
    results = {
        "success": [],
        "failed": []
    }
    
    try:
        for product in products:
            try:
                created = await grocy_client.create_product(
                    name=product.name,
                    location_id=product.location_id,
                    qu_id_stock=product.qu_id_stock,
                    description=product.description
                )
                
                results["success"].append({
                    "name": product.name,
                    "id": created["created_object_id"]
                })
                
            except Exception as e:
                results["failed"].append({
                    "name": product.name,
                    "reason": str(e)
                })
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating products: {str(e)}"
        )

