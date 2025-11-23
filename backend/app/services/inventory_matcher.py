import httpx
from typing import List, Dict, Any, Optional
import json


class InventoryMatcher:
    """
    LLM-powered service for parsing text and matching items to Grocy products
    """
    
    def __init__(self, llm_api_url: str, llm_api_key: str, llm_model: str):
        self.llm_api_url = llm_api_url.rstrip("/")
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self.headers = {
            "Authorization": f"Bearer {llm_api_key}",
            "Content-Type": "application/json"
        }
    
    def build_parse_prompt(
        self,
        input_text: str,
        grocy_products: List[Dict[str, Any]],
        grocy_locations: List[Dict[str, Any]],
        unit_preference: str = "metric"
    ) -> str:
        """
        Build prompt for parsing inventory text and matching to Grocy products
        """
        # Format products for LLM
        product_list = "\n".join([
            f"- ID: {p['id']}, Name: {p['name']}"
            for p in grocy_products
        ])
        
        # Format locations for LLM
        location_list = "\n".join([
            f"- ID: {loc['id']}, Name: {loc['name']}"
            for loc in grocy_locations
        ])
        
        unit_guidance = (
            "Use metric units (g, kg, ml, l) for quantities."
            if unit_preference == "metric"
            else "Use imperial units (oz, lb, fl oz, gal) for quantities."
        )
        
        prompt = f"""You are a grocery inventory assistant. Parse the following text and extract all food items with their quantities.

INPUT TEXT:
{input_text}

AVAILABLE GROCY PRODUCTS:
{product_list}

AVAILABLE STORAGE LOCATIONS:
{location_list}

TASK:
For each food item you find in the input text:
1. Extract the item name (normalized, e.g., "2% milk" -> "Milk", "org bnnas" -> "Organic Bananas")
2. Extract quantity as a number
3. Extract or infer the unit. {unit_guidance}
4. Match to the best Grocy product from the list above (use product ID)
5. Choose the most appropriate storage location (Fridge for perishables, Pantry for shelf-stable)
6. Assign confidence:
   - "high": Exact or near-exact match
   - "medium": Close match but some uncertainty
   - "low": Uncertain match
   - "new": No reasonable match found in Grocy products

IMPORTANT RULES:
- Convert units to {unit_preference} when possible (e.g., 1 gallon = 3.78 liters, 16 oz = 453 grams)
- If no match found, set matched_product_id to null and confidence to "new"
- Ignore non-food items (paper towels, cleaning supplies, etc.)
- Combine duplicate items (e.g., "2 apples" and "3 apples" = 5 apples)
- Use "count" as unit for whole items (eggs, apples, etc.)
- Common perishables go to Fridge: milk, eggs, meat, vegetables, fruits, cheese, yogurt
- Shelf-stable items go to Pantry: flour, sugar, canned goods, pasta, rice, spices

Return ONLY a valid JSON array with NO additional text or explanation:
[
  {{
    "original_text": "1gal 2% milk",
    "item_name": "Milk",
    "quantity": 3.78,
    "unit": "l",
    "matched_product_id": 5,
    "matched_product_name": "Milk",
    "confidence": "high",
    "suggested_location_id": 1,
    "suggested_location_name": "Fridge"
  }}
]"""
        
        return prompt
    
    async def parse_and_match(
        self,
        input_text: str,
        grocy_products: List[Dict[str, Any]],
        grocy_locations: List[Dict[str, Any]],
        unit_preference: str = "metric"
    ) -> List[Dict[str, Any]]:
        """
        Parse text and match items to Grocy products using LLM
        
        Returns:
            List of parsed items with matching information
        """
        prompt = self.build_parse_prompt(
            input_text,
            grocy_products,
            grocy_locations,
            unit_preference
        )
        
        payload = {
            "model": self.llm_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # Lower temperature for more consistent parsing
            "max_tokens": 3000
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.llm_api_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                llm_response = data["choices"][0]["message"]["content"]
                
                # Extract JSON from response (LLM might add markdown code blocks)
                llm_response = llm_response.strip()
                if llm_response.startswith("```json"):
                    llm_response = llm_response[7:]
                if llm_response.startswith("```"):
                    llm_response = llm_response[3:]
                if llm_response.endswith("```"):
                    llm_response = llm_response[:-3]
                llm_response = llm_response.strip()
                
                # Parse JSON
                parsed_items = json.loads(llm_response)
                return parsed_items
                
        except httpx.HTTPError as e:
            raise Exception(f"Error calling LLM API: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Error parsing LLM response as JSON: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Unexpected LLM response format: {str(e)}")
    
    def build_shopping_list_extraction_prompt(
        self,
        recipe_text: str,
        grocy_products: List[Dict[str, Any]],
        stock_info: Dict[str, Any],
        unit_preference: str = "metric"
    ) -> str:
        """
        Build prompt for extracting ingredients for shopping list with realistic purchasing quantities
        """
        # Format products for LLM
        product_list = "\n".join([
            f"- ID: {p['id']}, Name: {p['name']}"
            for p in grocy_products
        ])
        
        # Format stock info
        stock_list = "\n".join([
            f"- {item['name']}: {item['amount']} {item['unit']} (Product ID: {item['product_id']})"
            for item in stock_info.get('available_items', [])
        ])
        
        unit_guidance = (
            "Use metric purchasing units (kg, l) for quantities."
            if unit_preference == "metric"
            else "Use imperial purchasing units (lb, gal, qt) for quantities."
        )
        
        prompt = f"""You are a shopping list assistant. Extract ingredients from this recipe and convert them to REALISTIC PURCHASING QUANTITIES.

RECIPE TEXT:
{recipe_text}

AVAILABLE GROCY PRODUCTS:
{product_list}

CURRENT STOCK LEVELS:
{stock_list}

TASK:
For each ingredient in the recipe:
1. Extract ingredient name (normalized to match Grocy products)
2. **CONVERT to realistic purchasing quantity**:
   - Example: "2 tablespoons olive oil" → 1 bottle (750ml or 25 fl oz)
   - Example: "1 teaspoon salt" → 1 container (500g or 1 lb)
   - Example: "1/2 cup flour" → 1 bag (1kg or 2 lb)
   - Example: "1 cup milk" → 1 carton (1l or 1 qt)
   - **NEVER use teaspoons, tablespoons, or cups as purchasing units**
   - Think: "What would I actually buy at the store?"
3. Use realistic purchasing units. {unit_guidance}
4. Match to EXISTING Grocy product whenever possible
5. Check if in stock and if quantity is sufficient
6. Assign confidence (high/medium/low/new)

**PURCHASING UNIT GUIDELINES:**
- Spices/seasonings: 1 container (100g or 4 oz minimum)
- Oils: 1 bottle (500ml-1l or 16-32 fl oz)
- Flour/sugar: 1 bag (1-2 kg or 2-5 lb)
- Milk/liquids: 1 carton/bottle (1l or 1 qt minimum)
- Cheese: 1 package (200-500g or 8-16 oz)
- Produce: 1 unit or 1 bunch

Return ONLY a valid JSON array with NO additional text:
[
  {{
    "ingredient_text": "2 tablespoons olive oil",
    "product_id": 12,
    "product_name": "Olive Oil",
    "quantity": 750,
    "unit": "ml",
    "confidence": "high",
    "in_stock": false,
    "stock_amount": 0
  }}
]"""
        
        return prompt
    
    def build_recipe_extraction_prompt(
        self,
        recipe_text: str,
        grocy_products: List[Dict[str, Any]],
        stock_info: Dict[str, Any],
        unit_preference: str = "metric"
    ) -> str:
        """
        Build prompt for extracting ingredients from recipe text
        """
        # Format products for LLM
        product_list = "\n".join([
            f"- ID: {p['id']}, Name: {p['name']}"
            for p in grocy_products
        ])
        
        # Format stock info
        stock_list = "\n".join([
            f"- {item['name']}: {item['amount']} {item['unit']} (Product ID: {item['product_id']})"
            for item in stock_info.get('available_items', [])
        ])
        
        unit_guidance = (
            "Use metric units (g, kg, ml, l) for quantities."
            if unit_preference == "metric"
            else "Use imperial units (oz, lb, fl oz, gal) for quantities."
        )
        
        prompt = f"""You are a recipe analysis assistant. Extract all ingredients from this recipe and match them to EXISTING Grocy products.

RECIPE TEXT:
{recipe_text}

AVAILABLE GROCY PRODUCTS:
{product_list}

CURRENT STOCK LEVELS:
{stock_list}

TASK:
For each ingredient in the recipe:
1. Extract ingredient name (normalized to match Grocy products)
2. Extract quantity as a number
3. Extract unit. {unit_guidance}
4. **IMPORTANT**: Match to an EXISTING Grocy product from the list above whenever possible
   - Example: If recipe says "Parmesan Cheese" and Grocy has "Parmesan", use "Parmesan" (the existing product)
   - Example: If recipe says "2% Milk" and Grocy has "Milk", use "Milk" (the existing product)
   - Only mark as NEW if there's truly no reasonable match in the Grocy product list
5. Check if in stock and if quantity is sufficient
6. Assign confidence:
   - high: Exact match to existing product
   - medium: Close match to existing product
   - low: Uncertain match
   - new: No reasonable match found in Grocy products

Return ONLY a valid JSON array with NO additional text:
[
  {{
    "ingredient_text": "2 cups all-purpose flour",
    "product_id": 12,
    "product_name": "Flour",
    "quantity": 250,
    "unit": "g",
    "confidence": "high",
    "in_stock": true,
    "stock_amount": 1000
  }}
]"""
        
        return prompt
    
    async def extract_recipe_ingredients(
        self,
        recipe_text: str,
        grocy_products: List[Dict[str, Any]],
        stock_info: Dict[str, Any],
        unit_preference: str = "metric",
        for_shopping_list: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Extract ingredients from recipe text and match to Grocy products
        
        Args:
            for_shopping_list: If True, converts to realistic purchasing quantities
        
        Returns:
            List of recipe ingredients with matching and stock information
        """
        if for_shopping_list:
            prompt = self.build_shopping_list_extraction_prompt(
                recipe_text,
                grocy_products,
                stock_info,
                unit_preference
            )
        else:
            prompt = self.build_recipe_extraction_prompt(
                recipe_text,
                grocy_products,
                stock_info,
                unit_preference
            )
        
        payload = {
            "model": self.llm_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 3000
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.llm_api_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                llm_response = data["choices"][0]["message"]["content"]
                
                # Extract JSON from response
                llm_response = llm_response.strip()
                if llm_response.startswith("```json"):
                    llm_response = llm_response[7:]
                if llm_response.startswith("```"):
                    llm_response = llm_response[3:]
                if llm_response.endswith("```"):
                    llm_response = llm_response[:-3]
                llm_response = llm_response.strip()
                
                # Parse JSON
                ingredients = json.loads(llm_response)
                return ingredients
                
        except httpx.HTTPError as e:
            raise Exception(f"Error calling LLM API: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Error parsing LLM response as JSON: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Unexpected LLM response format: {str(e)}")

