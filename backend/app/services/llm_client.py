import httpx
from typing import Dict, Any, Optional, List
import json


class LLMClient:
    """Client for OpenAI-compatible LLM APIs"""
    
    def __init__(self, api_url: str, api_key: str, model: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def build_recipe_prompt(
        self,
        inventory: Dict[str, Any],
        request_params: Dict[str, Any],
        dietary_profiles: List[Dict[str, str]]
    ) -> str:
        """
        Build the prompt for recipe generation
        
        Args:
            inventory: Formatted inventory from Grocy
            request_params: Recipe generation parameters
            dietary_profiles: List of active dietary profiles
        
        Returns:
            Formatted prompt string
        """
        cuisine = request_params.get("cuisine", "No Preference")
        time_minutes = request_params.get("time_minutes", 60)
        effort_level = request_params.get("effort_level", "Medium")
        dish_preference = request_params.get("dish_preference", "I don't care")
        calories = request_params.get("calories_per_serving")
        use_external = request_params.get("use_external_ingredients", False)
        prioritize_expiring = request_params.get("prioritize_expiring", False)
        user_prompt = request_params.get("user_prompt", "")
        
        # Build the prompt
        prompt_parts = [
            "You are Elzar, an expert chef AI assistant! BAM! 🌶️",
            "",
            "Generate a delicious recipe based on the following information:",
            "",
            "AVAILABLE INGREDIENTS:"
        ]
        
        # Add available items
        if inventory.get("available_items"):
            for item in inventory["available_items"]:
                prompt_parts.append(
                    f"- {item['name']}: {item['amount']} {item['unit']}"
                )
        else:
            prompt_parts.append("- No inventory data available")
        
        prompt_parts.append("")
        prompt_parts.append("CONSTRAINTS:")
        prompt_parts.append(f"- Cuisine: {cuisine}")
        prompt_parts.append(f"- Maximum cooking time: {time_minutes} minutes")
        prompt_parts.append(f"- Effort level: {effort_level}")
        prompt_parts.append(f"- Dish cleanup preference: {dish_preference}")
        
        if calories:
            prompt_parts.append(f"- Target calories per serving: approximately {calories}")
        
        if use_external:
            prompt_parts.append(
                "- You MAY use ingredients not in the available list if needed"
            )
        else:
            prompt_parts.append(
                "- Try to ONLY use ingredients from the available list"
            )
        
        # Add dietary restrictions
        if dietary_profiles:
            prompt_parts.append("")
            prompt_parts.append("DIETARY RESTRICTIONS:")
            for profile in dietary_profiles:
                prompt_parts.append(
                    f"- {profile['name']}: {profile['dietary_restrictions']}"
                )
        
        # Add expiring ingredients
        if prioritize_expiring and inventory.get("expiring_soon"):
            prompt_parts.append("")
            prompt_parts.append(
                "INGREDIENTS EXPIRING SOON (please prioritize using these):"
            )
            for item in inventory["expiring_soon"]:
                prompt_parts.append(
                    f"- {item['name']}: {item['amount']} (expires {item['expiry_date']})"
                )
        
        # Add user's additional notes
        if user_prompt:
            prompt_parts.append("")
            prompt_parts.append(f"ADDITIONAL NOTES: {user_prompt}")
        
        # Instructions for output format
        prompt_parts.extend([
            "",
            "Please generate a detailed recipe in markdown format including:",
            "- Recipe title",
            "- Prep time and cook time",
            "- Number of servings",
            "- Ingredients list with quantities",
            "- Step-by-step instructions",
            "- Estimated calories per serving (if possible)",
            "- Any relevant cooking tips",
            "",
            "At the end, include metadata in this exact format:",
            "---",
            "METADATA:",
            "Cuisine: [the cuisine type]",
            "Total Time: [number in minutes]",
            "Effort: [Low/Medium/High]",
            "Calories: [number per serving]",
            "---",
            "",
            "BAM! Let's make something delicious! 🌶️"
        ])
        
        return "\n".join(prompt_parts)
    
    async def generate_recipe(
        self,
        inventory: Dict[str, Any],
        request_params: Dict[str, Any],
        dietary_profiles: List[Dict[str, str]]
    ) -> str:
        """
        Generate a recipe using the LLM
        
        Returns:
            Generated recipe text
        """
        prompt = self.build_recipe_prompt(inventory, request_params, dietary_profiles)
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.api_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                recipe_text = data["choices"][0]["message"]["content"]
                return recipe_text
                
        except httpx.HTTPError as e:
            raise Exception(f"Error calling LLM API: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Unexpected LLM response format: {str(e)}")
    
    async def regenerate_recipe(
        self,
        previous_recipe: str,
        inventory: Dict[str, Any],
        request_params: Dict[str, Any],
        dietary_profiles: List[Dict[str, str]]
    ) -> str:
        """
        Regenerate a recipe with the same parameters but different result
        
        Args:
            previous_recipe: The previous recipe to avoid
            inventory: Formatted inventory from Grocy
            request_params: Recipe generation parameters
            dietary_profiles: List of active dietary profiles
        
        Returns:
            New generated recipe text
        """
        base_prompt = self.build_recipe_prompt(
            inventory, request_params, dietary_profiles
        )
        
        # Add instruction to generate something different
        prompt = (
            f"{base_prompt}\n\n"
            "NOTE: Please generate a DIFFERENT recipe than before. "
            "Try a different approach or technique to create variety!"
        )
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.9,  # Higher temperature for more variety
            "max_tokens": 2000
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.api_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                recipe_text = data["choices"][0]["message"]["content"]
                return recipe_text
                
        except httpx.HTTPError as e:
            raise Exception(f"Error calling LLM API: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Unexpected LLM response format: {str(e)}")

