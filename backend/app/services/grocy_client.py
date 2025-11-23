import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime


class GrocyClient:
    """Client for interacting with Grocy API"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "GROCY-API-KEY": api_key,
            "Accept": "application/json"
        }
    
    async def get_stock(self) -> List[Dict[str, Any]]:
        """Get current stock/inventory from Grocy"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/stock",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_volatile_stock(self) -> List[Dict[str, Any]]:
        """Get stock with expiration information (volatile stock)"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/stock/volatile",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_products(self) -> List[Dict[str, Any]]:
        """Get all products"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/objects/products",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_product_details(self, product_id: int) -> Dict[str, Any]:
        """Get details for a specific product"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/stock/products/{product_id}",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def format_inventory_for_llm(
        self, 
        prioritize_expiring: bool = False
    ) -> Dict[str, Any]:
        """
        Format Grocy inventory into a structure suitable for LLM prompts
        
        Returns a dict with:
        - available_items: List of items with quantities
        - expiring_soon: List of items expiring soon (if prioritize_expiring)
        """
        try:
            stock = await self.get_stock()
            volatile_stock = await self.get_volatile_stock() if prioritize_expiring else []
            products = await self.get_products()
            
            # Create a product lookup
            product_lookup = {p["id"]: p for p in products}
            
            # Format available items
            available_items = []
            for item in stock:
                product_id = item.get("product_id")
                product = product_lookup.get(product_id, {})
                
                available_items.append({
                    "name": product.get("name", "Unknown"),
                    "amount": item.get("amount", 0),
                    "unit": item.get("quantity_unit_stock", {}).get("name", "unit"),
                    "product_id": product_id
                })
            
            result = {
                "available_items": available_items,
                "expiring_soon": []
            }
            
            # Add expiring items if requested
            if prioritize_expiring and volatile_stock:
                expiring_items = []
                for item in volatile_stock:
                    product_id = item.get("product_id")
                    product = product_lookup.get(product_id, {})
                    best_before = item.get("best_before_date")
                    
                    if best_before:
                        expiring_items.append({
                            "name": product.get("name", "Unknown"),
                            "amount": item.get("amount", 0),
                            "expiry_date": best_before,
                            "product_id": product_id
                        })
                
                # Sort by expiry date
                expiring_items.sort(key=lambda x: x["expiry_date"])
                result["expiring_soon"] = expiring_items[:10]  # Top 10 expiring
            
            return result
            
        except httpx.HTTPError as e:
            raise Exception(f"Error fetching Grocy inventory: {str(e)}")
    
    async def add_recipe_to_grocy(
        self, 
        recipe_name: str, 
        ingredients: List[Dict[str, Any]]
    ) -> int:
        """
        Add a recipe to Grocy (future feature)
        
        Args:
            recipe_name: Name of the recipe
            ingredients: List of ingredients with product_id and amount
        
        Returns:
            Recipe ID
        """
        # TODO: Implement recipe creation in Grocy
        # This will be part of Phase 10 (Future Features)
        raise NotImplementedError("Recipe creation in Grocy not yet implemented")
    
    async def add_to_shopping_list(
        self, 
        product_id: int, 
        amount: float
    ) -> Dict[str, Any]:
        """
        Add an item to Grocy shopping list (future feature)
        """
        # TODO: Implement shopping list addition
        # This will be part of Phase 10 (Future Features)
        raise NotImplementedError("Shopping list addition not yet implemented")
    
    async def consume_product(
        self, 
        product_id: int, 
        amount: float, 
        spoiled: bool = False
    ) -> Dict[str, Any]:
        """
        Mark a product as consumed in Grocy (future feature)
        """
        # TODO: Implement product consumption
        # This will be part of Phase 10 (Future Features)
        raise NotImplementedError("Product consumption not yet implemented")

