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
    
    async def get_locations(self) -> List[Dict[str, Any]]:
        """Get all storage locations from Grocy"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/objects/locations",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def create_location(self, name: str, description: str = "") -> Dict[str, Any]:
        """
        Create a new storage location in Grocy
        
        Args:
            name: Location name (e.g., "Pantry", "Fridge")
            description: Optional description
        
        Returns:
            Created location details
        """
        body = {
            "name": name,
            "description": description,
            "is_freezer": 1 if "freez" in name.lower() else 0
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/objects/locations",
                headers=self.headers,
                json=body,
                timeout=30.0
            )
            
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error_message', response.text)
                except:
                    error_msg = response.text or "Unknown error"
                
                raise Exception(f"Grocy API error: {response.status_code} - {error_msg}")
            
            return response.json()
    
    async def get_quantity_units(self) -> List[Dict[str, Any]]:
        """Get all quantity units from Grocy"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/objects/quantity_units",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def purchase_product(
        self,
        product_id: int,
        amount: float,
        best_before_date: Optional[str] = None,
        price: Optional[float] = None,
        location_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Add stock to a product (purchase/add)
        
        Args:
            product_id: Grocy product ID
            amount: Quantity to add
            best_before_date: Optional expiration date (YYYY-MM-DD)
            price: Optional price paid
            location_id: Optional storage location ID
        
        Returns:
            Transaction details
        """
        body = {
            "amount": amount,
            "transaction_type": "purchase"
        }
        
        if best_before_date:
            body["best_before_date"] = best_before_date
        if price is not None:
            body["price"] = price
        if location_id is not None:
            body["location_id"] = location_id
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/stock/products/{product_id}/add",
                headers=self.headers,
                json=body,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def consume_product(
        self, 
        product_id: int, 
        amount: float, 
        spoiled: bool = False,
        location_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Remove stock from a product (consume/use)
        
        Args:
            product_id: Grocy product ID
            amount: Quantity to consume
            spoiled: Whether the product was spoiled
            location_id: Optional location to consume from
        
        Returns:
            Transaction details
        """
        body = {
            "amount": amount,
            "transaction_type": "consume",
            "spoiled": spoiled
        }
        
        if location_id is not None:
            body["location_id"] = location_id
        
        print(f"🔍 Consuming product {product_id}: amount={amount}, location_id={location_id}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/stock/products/{product_id}/consume",
                headers=self.headers,
                json=body,
                timeout=30.0
            )
            
            if response.status_code != 200:
                # Try to get error details from Grocy
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error_message', response.text)
                except:
                    error_msg = response.text or "Unknown error"
                
                raise Exception(f"Grocy API error: {response.status_code} - {error_msg}")
            
            return response.json()
    
    async def create_product(
        self,
        name: str,
        location_id: int,
        qu_id_stock: int,
        qu_id_purchase: Optional[int] = None,
        description: str = "",
        min_stock_amount: int = 0
    ) -> Dict[str, Any]:
        """
        Create a new product in Grocy
        
        Args:
            name: Product name
            location_id: Default storage location ID
            qu_id_stock: Quantity unit ID for stock
            qu_id_purchase: Quantity unit ID for purchase (defaults to stock unit)
            description: Optional product description
            min_stock_amount: Minimum stock amount for warnings
        
        Returns:
            Created product details
        """
        body = {
            "name": name,
            "description": description or name,
            "location_id": location_id,
            "qu_id_stock": qu_id_stock,
            "qu_id_purchase": qu_id_purchase or qu_id_stock,
            "qu_id_consume": qu_id_stock,  # Same as stock unit
            "qu_id_price": qu_id_stock,  # Same as stock unit
            "min_stock_amount": min_stock_amount,
            "default_best_before_days": 0,
            "product_group_id": None,
            "active": 1,
            "calories": 0,
            "quick_consume_amount": 1,
            "due_type": 1,  # Best before date
            "treat_opened_as_out_of_stock": 1
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/objects/products",
                    headers=self.headers,
                    json=body,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                # Log the error details for debugging
                error_detail = f"Grocy API error: {e.response.status_code} - {e.response.text}"
                print(f"❌ Failed to create product '{name}': {error_detail}")
                raise Exception(error_detail)
    
    async def create_quantity_unit(
        self,
        name: str,
        name_plural: Optional[str] = None,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Create a new quantity unit in Grocy
        
        Args:
            name: Unit name (singular)
            name_plural: Plural form (defaults to name + 's')
            description: Optional description
        
        Returns:
            Created quantity unit details
        """
        body = {
            "name": name,
            "name_plural": name_plural or (name + "s"),
            "description": description,
            "active": 1
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/objects/quantity_units",
                    headers=self.headers,
                    json=body,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = f"Grocy API error: {e.response.status_code} - {e.response.text}"
                print(f"❌ Failed to create quantity unit '{name}': {error_detail}")
                raise Exception(error_detail)
    
    async def create_quantity_unit_conversion(
        self,
        from_qu_id: int,
        to_qu_id: int,
        factor: float
    ) -> Dict[str, Any]:
        """
        Create a quantity unit conversion in Grocy
        
        Args:
            from_qu_id: Source quantity unit ID
            to_qu_id: Target quantity unit ID
            factor: Conversion factor (from * factor = to)
        
        Returns:
            Created conversion details
        """
        body = {
            "from_qu_id": from_qu_id,
            "to_qu_id": to_qu_id,
            "factor": factor
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/objects/quantity_unit_conversions",
                    headers=self.headers,
                    json=body,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = f"Grocy API error: {e.response.status_code} - {e.response.text}"
                print(f"❌ Failed to create unit conversion: {error_detail}")
                raise Exception(error_detail)
    
    async def add_to_shopping_list(
        self, 
        product_id: int, 
        amount: float,
        list_id: Optional[int] = None,
        note: str = ""
    ) -> Dict[str, Any]:
        """
        Add an item to Grocy shopping list
        
        Args:
            product_id: Grocy product ID
            amount: Quantity to add
            list_id: Optional shopping list ID (default list if None)
            note: Optional note
        
        Returns:
            Shopping list item details
        """
        body = {
            "product_id": product_id,
            "product_amount": amount,
            "note": note
        }
        
        if list_id is not None:
            body["list_id"] = list_id
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/stock/shoppinglist/add-product",
                headers=self.headers,
                json=body,
                timeout=30.0
            )
            response.raise_for_status()
            
            # Grocy shopping list endpoint may return empty response
            if response.status_code == 204 or not response.text:
                return {"success": True, "product_id": product_id}
            
            return response.json()
    
    async def create_recipe(
        self,
        name: str,
        description: str,
        base_servings: int = 1,
        desired_servings: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a recipe in Grocy
        
        Args:
            name: Recipe name
            description: Full recipe text/instructions
            base_servings: Base number of servings
            desired_servings: Desired servings (defaults to base_servings)
        
        Returns:
            Created recipe details with recipe_id
        """
        body = {
            "name": name,
            "description": description,
            "base_servings": base_servings,
            "desired_servings": desired_servings or base_servings,
            "type": "normal"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/objects/recipes",
                headers=self.headers,
                json=body,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def add_recipe_ingredient(
        self,
        recipe_id: int,
        product_id: int,
        amount: float,
        qu_id: int,
        note: str = ""
    ) -> Dict[str, Any]:
        """
        Add an ingredient to a recipe
        
        Args:
            recipe_id: Grocy recipe ID
            product_id: Grocy product ID
            amount: Quantity needed
            qu_id: Quantity unit ID
            note: Optional note (e.g., "chopped", "diced")
        
        Returns:
            Recipe ingredient details
        """
        body = {
            "recipe_id": recipe_id,
            "product_id": product_id,
            "amount": amount,
            "qu_id": qu_id,
            "note": note,
            "variable_amount": "",
            "only_check_single_unit_in_stock": 0
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/objects/recipes_pos",
                headers=self.headers,
                json=body,
                timeout=30.0
            )
            
            if response.status_code != 200:
                error_detail = ""
                try:
                    error_detail = response.json()
                except:
                    error_detail = response.text
                raise Exception(f"Grocy API error: {response.status_code} - {error_detail}")
            
            return response.json()

