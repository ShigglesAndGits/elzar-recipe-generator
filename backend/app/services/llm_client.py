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
        
        # New parameters
        elzar_voice = request_params.get("elzar_voice", True)
        servings = request_params.get("servings", "3-4")
        high_leftover_potential = request_params.get("high_leftover_potential", False)
        
        # Build the prompt
        prompt_parts = []
        
        if elzar_voice:
            prompt_parts.append("You are Elzar, an expert chef AI assistant! BAM! 🌶️")
            prompt_parts.append("You should speak in the voice of Elzar from Futurama (enthusiastic, using phrases like 'BAM!', 'Kick it up a notch', 'Spice Weasel').")
        else:
            prompt_parts.append("You are a professional chef AI assistant.")
            prompt_parts.append("Provide ONLY the recipe details. Calorie count, ingredients list, and instructions. NO fluff, NO conversational filler, NO intro/outro text.")
            
        prompt_parts.extend([
            "",
            "Generate a recipe based on the following information:",
            "",
            "AVAILABLE INGREDIENTS:"
        ])
        
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
        prompt_parts.append(f"- Servings: {servings}")
        
        if servings == "7+":
            prompt_parts.append("  (This is a large batch for food prep. Scale ingredients accordingly.)")
            
        if high_leftover_potential:
            prompt_parts.append("- High Leftover Potential: Ensure this recipe stores well and makes for good leftovers.")
        
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
            "OUTPUT FORMAT:",
            "1. FIRST LINE MUST BE: **Calories:** [count] | **Servings:** [count] | **Prep Time:** [time]",
            "2. Then, the Recipe Title",
            "3. Ingredients list with quantities - SEPARATE into two subsections: 'From Pantry' (items from available list) and 'Missing / To Buy' (items not in inventory)",
            "4. Step-by-step instructions",
            "5. Any relevant cooking tips",
            ""
        ])
        
        if not elzar_voice:
             prompt_parts.append("REMEMBER: No conversational filler. Just the facts.")
             
        prompt_parts.extend([
            "",
            "At the VERY end, include metadata in this exact format:",
            "---",
            "METADATA:",
            "Cuisine: [the cuisine type]",
            "Total Time: [number in minutes]",
            "Effort: [Low/Medium/High]",
            "Calories: [number per serving]",
            "---"
        ])
        
        if elzar_voice:
             prompt_parts.append("")
             prompt_parts.append("BAM! Let's make something delicious! 🌶️")
        
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
    async def format_recipe_for_grocy(self, recipe_text: str) -> str:
        """
        Reformat recipe text for Grocy storage - strip Elzar's voice and format cleanly
        
        Args:
            recipe_text: Original recipe text (possibly with Elzar's voice)
        
        Returns:
            Clean, structured recipe text suitable for Grocy
        """
        prompt = f"""Reformat this recipe for clean storage in a recipe database. Remove ALL conversational language, narrator's voice, and personality. Provide ONLY the essential recipe information in a clean, structured format.

ORIGINAL RECIPE:
{recipe_text}

REQUIRED FORMAT:
**Calories:** [number] | **Servings:** [number] | **Prep Time:** [time]
**Cuisine:** [cuisine type]

**Ingredients:**
- [ingredient 1]
- [ingredient 2]
...

**Instructions:**
1. [step 1]
2. [step 2]
...

RULES:
- NO conversational language or personality
- NO "BAM!", "Kick it up a notch", or similar phrases
- NO introductions or conclusions
- NO jokes or commentary
- ONLY factual recipe information
- Keep it professional and concise
- Preserve all measurements and quantities exactly
- Maintain clear structure with proper line breaks

Provide ONLY the reformatted recipe with NO additional text."""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
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
                formatted_text = data["choices"][0]["message"]["content"]
                return formatted_text
                
        except httpx.HTTPError as e:
            raise Exception(f"Error calling LLM API: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Unexpected LLM response format: {str(e)}")

