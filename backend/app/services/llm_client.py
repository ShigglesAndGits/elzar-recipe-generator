import httpx
from typing import Dict, Any, Optional, List
import json


class LLMClient:
    """Client for OpenAI-compatible LLM APIs"""

    def __init__(self, api_url: str, api_key: str, model: str, max_tokens: int = 16000):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def build_recipe_prompt(
        self,
        inventory: Dict[str, Any],
        request_params: Dict[str, Any],
        dietary_profiles: List[Dict[str, str]],
        user_preferences: str = ""
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
        bulk_prep = request_params.get("bulk_prep", False)
        high_leftover_potential = request_params.get("high_leftover_potential", False)
        unit_preference = request_params.get("unit_preference", "imperial")
        custom_persona = request_params.get("custom_persona", "You are a professional chef and nutritionist.")

        # Build the prompt
        prompt_parts = []

        # Start with user's custom persona
        prompt_parts.append(custom_persona)

        # Add Elzar voice on top if enabled
        if elzar_voice:
            prompt_parts.append("You deliver your responses in the voice of Elzar, the TV chef from Futurama. Use 'BAM!' once or twice, maybe mention 'Kick it up a notch' or 'Spice Weasel' sparingly. Keep it fun but don't overdo it. Focus on the recipe, with just a dash of personality.")
        else:
            prompt_parts.append("Provide ONLY the recipe details. Calorie count, ingredients list, and instructions. NO fluff, NO conversational filler, NO intro/outro text.")
            
        # Add user preferences if available
        if user_preferences:
            prompt_parts.extend([
                "",
                "USER PREFERENCES (take these into account for all suggestions):",
                user_preferences,
            ])

        prompt_parts.extend([
            "",
            "Generate a recipe based on the following information:",
            ""
        ])

        # Check if we have inventory data
        has_inventory = bool(inventory.get("available_items"))

        # Add available items only if we have inventory
        if has_inventory:
            prompt_parts.append("AVAILABLE INGREDIENTS:")
            for item in inventory["available_items"]:
                prompt_parts.append(
                    f"- {item['name']}: {item['amount']} {item['unit']}"
                )
            prompt_parts.append("")

        prompt_parts.append("CONSTRAINTS:")
        prompt_parts.append(f"- Cuisine: {cuisine}")
        prompt_parts.append(f"- Maximum cooking time: {time_minutes} minutes")
        prompt_parts.append(f"- Effort level: {effort_level}")
        prompt_parts.append(f"- Dish cleanup preference: {dish_preference}")
        prompt_parts.append(f"- Servings: {servings}")

        if servings == "7+":
            prompt_parts.append("  (This is a large batch for food prep. Scale ingredients accordingly.)")

        if bulk_prep:
            prompt_parts.append("")
            prompt_parts.append("🧊 BULK PREP MODE ENABLED:")
            prompt_parts.append("This recipe MUST be suitable for bulk meal prep with the following requirements:")
            prompt_parts.append("- Choose foods that FREEZE WELL (avoid: cream-based sauces, raw vegetables that go soggy, mayonnaise-based dishes)")
            prompt_parts.append("- Recipe should be portionable into SINGLE-SERVING containers or wrapped in foil")
            prompt_parts.append("- Must REHEAT WELL from frozen - either in microwave, oven, or on stovetop")
            prompt_parts.append("- Include clear storage instructions: how to portion, container recommendations, and freezer shelf life")
            prompt_parts.append("- Include reheating instructions: from frozen cook times/temps for microwave and oven")
            prompt_parts.append("- Good bulk prep foods: casseroles, stews, soups, burritos, meatballs, marinated proteins, grain bowls, lasagna, enchiladas")
            prompt_parts.append("- Make at least 8 servings for proper bulk prep")

        if high_leftover_potential:
            prompt_parts.append("- High Leftover Potential: Ensure this recipe stores well and makes for good leftovers.")

        if calories:
            prompt_parts.append(f"- Target calories per serving: approximately {calories}")

        # Only add inventory usage constraints if we have inventory
        if has_inventory:
            if use_external:
                prompt_parts.append(
                    "- You MAY use ingredients not in the available list if needed"
                )
            else:
                prompt_parts.append(
                    "- Try to ONLY use ingredients from the available list"
                )
        
        # Add available equipment
        available_equipment = request_params.get("available_equipment", [])
        if available_equipment:
            prompt_parts.append("")
            prompt_parts.append("AVAILABLE KITCHEN EQUIPMENT:")
            for equipment in available_equipment:
                prompt_parts.append(f"- {equipment}")
            prompt_parts.append("IMPORTANT: Only use cooking methods that work with the available equipment listed above.")
        
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
        unit_system = "imperial units (oz, lb, cups, tbsp, tsp, etc.)" if unit_preference == "imperial" else "metric units (g, kg, ml, l, etc.)"

        prompt_parts.extend([
            "",
            "OUTPUT FORMAT:",
            "1. FIRST LINE MUST BE: **Calories:** [count] | **Servings:** [count] | **Prep Time:** [time] | **Est. Cost:** $[amount]",
            "   (Est. Cost is your best estimate for total ingredient cost in USD based on typical grocery prices)",
            "2. Then, the Recipe Title",
        ])

        # Ingredient list format depends on whether we have inventory
        if has_inventory:
            prompt_parts.append(f"3. Ingredients list with quantities in {unit_system} - SEPARATE into two subsections: 'From Pantry' (items from available list) and 'Missing / To Buy' (items not in inventory)")
        else:
            prompt_parts.append(f"3. Ingredients list with quantities in {unit_system}")

        prompt_parts.extend([
            "   Example format: 'Flour: 2 cups' or 'Olive Oil: 3 tbsp' or 'Chicken: 1 lb'",
            "   ALWAYS include the unit (cups, tbsp, oz, lb, etc.) - NEVER just write a number without a unit!",
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
            "Estimated Cost: [dollar amount, e.g. 12.50]",
            "",
            "NUTRITION:",
            "Rate how good a source of each nutrient this recipe is (1 = poor/none, 10 = excellent source).",
            "Protein: [1-10]/10",
            "Carbs: [1-10]/10",
            "Fiber: [1-10]/10",
            "Healthy Fats: [1-10]/10",
            "Vitamin A: [1-10]/10",
            "Vitamin C: [1-10]/10",
            "Vitamin D: [1-10]/10",
            "Vitamin B12: [1-10]/10",
            "Vitamin K: [1-10]/10",
            "Iron: [1-10]/10",
            "Calcium: [1-10]/10",
            "Potassium: [1-10]/10",
            "Magnesium: [1-10]/10",
            "Zinc: [1-10]/10",
            "Omega-3: [1-10]/10",
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
        dietary_profiles: List[Dict[str, str]],
        user_preferences: str = ""
    ) -> str:
        """
        Generate a recipe using the LLM

        Returns:
            Generated recipe text
        """
        prompt = self.build_recipe_prompt(inventory, request_params, dietary_profiles, user_preferences)
        
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

    async def generate_advice(
        self,
        question: str,
        inventory: Dict[str, Any],
        request_params: Dict[str, Any],
        dietary_profiles: List[Dict[str, str]],
        user_preferences: str = ""
    ) -> str:
        """
        Generate cooking/food advice based on user's question.

        Args:
            question: The user's question
            inventory: Available ingredients from Grocy
            request_params: Parameters including persona and voice settings
            dietary_profiles: Active dietary restriction profiles

        Returns:
            Advice response text
        """
        custom_persona = request_params.get("custom_persona", "You are a professional chef and nutritionist.")
        elzar_voice = request_params.get("elzar_voice", False)
        unit_preference = request_params.get("unit_preference", "imperial")

        prompt_parts = []

        # Start with persona
        prompt_parts.append(custom_persona)

        # Add Elzar voice if enabled
        if elzar_voice:
            prompt_parts.append("You deliver your responses in the voice of Elzar, the TV chef from Futurama. Use 'BAM!' occasionally, maybe mention 'Kick it up a notch' or 'Spice Weasel' sparingly. Keep it fun but informative.")

        # Add user preferences if available
        if user_preferences:
            prompt_parts.extend([
                "",
                "USER PREFERENCES (take these into account for all suggestions):",
                user_preferences,
            ])

        prompt_parts.extend([
            "",
            "A user has a cooking or food-related question. Please provide helpful, practical advice.",
            ""
        ])

        # Add inventory context if available
        if inventory.get("available_items"):
            prompt_parts.append("FOR CONTEXT - The user has these ingredients available:")
            for item in inventory["available_items"][:30]:
                prompt_parts.append(f"- {item['name']}: {item['amount']} {item['unit']}")
            prompt_parts.append("")

        # Add dietary restrictions
        if dietary_profiles:
            prompt_parts.append("DIETARY RESTRICTIONS TO CONSIDER:")
            for profile in dietary_profiles:
                prompt_parts.append(f"- {profile['name']}: {profile['dietary_restrictions']}")
            prompt_parts.append("")

        # Add the question
        prompt_parts.extend([
            "USER'S QUESTION:",
            question,
            "",
            f"Please provide helpful advice. Use {unit_preference} units if measurements are needed.",
            "Keep your response concise but thorough. If the question involves ingredients, consider what they have available."
        ])

        if elzar_voice:
            prompt_parts.append("")
            prompt_parts.append("BAM! Let's help them out! 🌶️")

        prompt = "\n".join(prompt_parts)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1500
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
                advice_text = data["choices"][0]["message"]["content"]
                return advice_text

        except httpx.HTTPError as e:
            raise Exception(f"Error calling LLM API: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Unexpected LLM response format: {str(e)}")

    async def regenerate_recipe(
        self,
        previous_recipe: str,
        inventory: Dict[str, Any],
        request_params: Dict[str, Any],
        dietary_profiles: List[Dict[str, str]],
        user_preferences: str = ""
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
            inventory, request_params, dietary_profiles, user_preferences
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

    def build_meal_plan_prompt(
        self,
        inventory: Dict[str, Any],
        request_params: Dict[str, Any],
        dietary_profiles: List[Dict[str, str]],
        user_preferences: str = ""
    ) -> str:
        """
        Build the prompt for meal plan generation

        Args:
            inventory: Formatted inventory from Grocy
            request_params: Meal plan generation parameters
            dietary_profiles: List of active dietary profiles

        Returns:
            Formatted prompt string
        """
        days = request_params.get("days", 7)
        people = request_params.get("people", 2)

        generate_breakfast = request_params.get("generate_breakfast", True)
        generate_lunch = request_params.get("generate_lunch", True)
        generate_dinner = request_params.get("generate_dinner", True)
        generate_snacks = request_params.get("generate_snacks", False)

        budget_level = request_params.get("budget_level", "moderate")
        daily_calorie_target = request_params.get("daily_calorie_target")

        breakfast_effort = request_params.get("breakfast_effort", 2)
        lunch_effort = request_params.get("lunch_effort", 2)
        dinner_effort = request_params.get("dinner_effort", 3)
        snack_effort = request_params.get("snack_effort", 1)

        variety_level = request_params.get("variety_level", 3)
        use_inventory = request_params.get("use_inventory", True)
        prioritize_expiring = request_params.get("prioritize_expiring", False)
        user_prompt = request_params.get("user_prompt", "")
        unit_preference = request_params.get("unit_preference", "imperial")

        # Budget descriptions
        budget_descriptions = {
            "broke": "extremely tight budget - focus on the cheapest possible ingredients like rice, beans, pasta, eggs",
            "dirt_cheap": "very low budget - prioritize inexpensive staples and bulk ingredients",
            "cheap": "budget-conscious - use affordable ingredients, avoid expensive proteins and specialty items",
            "moderate": "reasonable budget - balance cost and quality, occasional premium ingredients",
            "high": "comfortable budget - quality ingredients, variety of proteins and fresh produce",
            "luxury": "no budget constraints - premium ingredients, specialty items, restaurant-quality"
        }

        # Effort level descriptions
        effort_descriptions = {
            1: "pre-packaged/minimal prep (microwave meals, sandwiches, ready-to-eat)",
            2: "quick and easy (15-20 min, simple cooking)",
            3: "moderate effort (30-45 min, standard cooking)",
            4: "involved (45-60 min, multiple components)",
            5: "high effort (60+ min, complex techniques)"
        }

        # Variety descriptions - ranges from ingredient reuse to maximum variety
        variety_descriptions = {
            1: "Please think of multiple meals, but try to RE-USE INGREDIENTS between meals as much as possible. Repeating a meal for a few days is totally okay. Buy ingredients in bulk and use them across multiple recipes.",
            2: "Focus on ingredient efficiency - some overlap between meals is encouraged to reduce shopping complexity. A few repeated meals are fine.",
            3: "Don't worry too much about reusing ingredients between meals. Some overlap is good but it's not critical. Balance between variety and practicality.",
            4: "Prioritize variety - diverse meals with only occasional strategic ingredient overlap. Each day should feel different.",
            5: "Please make EVERY MEAL UNIQUE, focusing on maximum variety. Different cuisines, different ingredients, different cooking methods. Avoid any repetition."
        }

        # Count meals
        meals_list = []
        if generate_breakfast:
            meals_list.append("breakfast")
        if generate_lunch:
            meals_list.append("lunch")
        if generate_dinner:
            meals_list.append("dinner")
        if generate_snacks:
            meals_list.append("snacks")

        custom_persona = request_params.get("custom_persona", "You are a professional chef and nutritionist.")

        prompt_parts = [
            f"{custom_persona} Generate a detailed meal plan based on the following requirements.",
        ]

        if user_preferences:
            prompt_parts.extend([
                "",
                "USER PREFERENCES (take these into account for all suggestions):",
                user_preferences,
            ])

        prompt_parts.extend([
            "",
            f"MEAL PLAN PARAMETERS:",
            f"- Duration: {days} days",
            f"- Number of people: {people}",
            f"- Meals to plan: {', '.join(meals_list)}",
            f"- Budget: {budget_level.upper()} - {budget_descriptions.get(budget_level, 'moderate budget')}",
            ""
        ])

        if daily_calorie_target:
            prompt_parts.append(f"CALORIE TARGET: {daily_calorie_target} calories per day per person")
            prompt_parts.append("IMPORTANT: Each meal should contribute appropriately to this daily target.")
            if not generate_breakfast or not generate_lunch or not generate_dinner:
                prompt_parts.append("Since not all meals are being planned, allocate calories proportionally to the meals being generated.")
            prompt_parts.append("")

        prompt_parts.extend([
            "EFFORT LEVELS:",
        ])

        if generate_breakfast:
            prompt_parts.append(f"- Breakfast: {effort_descriptions.get(breakfast_effort, 'moderate')}")
        if generate_lunch:
            prompt_parts.append(f"- Lunch: {effort_descriptions.get(lunch_effort, 'moderate')}")
        if generate_dinner:
            prompt_parts.append(f"- Dinner: {effort_descriptions.get(dinner_effort, 'moderate')}")
        if generate_snacks:
            prompt_parts.append(f"- Snacks: {effort_descriptions.get(snack_effort, 'minimal')}")

        prompt_parts.extend([
            "",
            f"VARIETY LEVEL: {variety_level}/5 - {variety_descriptions.get(variety_level, 'balanced variety')}",
            ""
        ])

        # Add inventory if enabled
        if use_inventory and inventory.get("available_items"):
            prompt_parts.append("AVAILABLE INGREDIENTS (from pantry/fridge):")
            for item in inventory["available_items"][:50]:  # Limit to avoid token overflow
                prompt_parts.append(f"- {item['name']}: {item['amount']} {item['unit']}")
            prompt_parts.append("")

            if prioritize_expiring and inventory.get("expiring_soon"):
                prompt_parts.append("INGREDIENTS EXPIRING SOON (prioritize these!):")
                for item in inventory["expiring_soon"]:
                    prompt_parts.append(f"- {item['name']}: {item['amount']} (expires {item['expiry_date']})")
                prompt_parts.append("")

        # Add dietary restrictions
        if dietary_profiles:
            prompt_parts.append("DIETARY RESTRICTIONS:")
            for profile in dietary_profiles:
                prompt_parts.append(f"- {profile['name']}: {profile['dietary_restrictions']}")
            prompt_parts.append("")

        # Add user notes
        if user_prompt:
            prompt_parts.append(f"ADDITIONAL NOTES: {user_prompt}")
            prompt_parts.append("")

        # Output format instructions
        unit_system = "imperial units (oz, lb, cups, tbsp, tsp)" if unit_preference == "imperial" else "metric units (g, kg, ml, l)"

        prompt_parts.extend([
            "OUTPUT FORMAT:",
            "You MUST use the following exact format with the delimiter '===RECIPE===' to separate each recipe.",
            "",
            "First, provide a brief overview paragraph about the meal plan, including an estimated total cost for all meals.",
            "",
            "Then for EACH meal, use this EXACT format:",
            "",
            "===RECIPE===",
            "DAY: [number]",
            "MEAL: [breakfast/lunch/dinner/snack]",
            "TITLE: [Recipe Name]",
            "CALORIES: [estimated calories per serving]",
            "PREP_TIME: [time in minutes]",
            "SERVINGS: [number]",
            "ESTIMATED_COST: [estimated total cost in USD, e.g. 8.50]",
            "",
            "**Ingredients:**",
            f"- [ingredient with quantity in {unit_system}]",
            "- [ingredient with quantity]",
            "...",
            "",
            "**Instructions:**",
            "1. [step]",
            "2. [step]",
            "...",
            "",
            "**Tips:** [optional quick tip]",
            "===END_RECIPE===",
            "",
            "CRITICAL RULES:",
            "1. Every recipe MUST start with ===RECIPE=== and end with ===END_RECIPE===",
            "2. Include ALL requested meals for ALL days",
            "3. Keep recipes concise but complete",
            "4. Match effort levels appropriately",
            "5. Stay within budget constraints",
            f"6. Scale all recipes for {people} people",
            "7. Estimate costs based on typical US grocery prices",
            ""
        ])

        return "\n".join(prompt_parts)

    async def generate_meal_plan(
        self,
        inventory: Dict[str, Any],
        request_params: Dict[str, Any],
        dietary_profiles: List[Dict[str, str]],
        user_preferences: str = ""
    ) -> str:
        """
        Generate a meal plan using the LLM

        Returns:
            Generated meal plan text with delimiter-separated recipes
        """
        prompt = self.build_meal_plan_prompt(inventory, request_params, dietary_profiles, user_preferences)

        # Calculate expected output size based on number of meals
        days = request_params.get("days", 7)
        meals_per_day = sum([
            request_params.get("generate_breakfast", True),
            request_params.get("generate_lunch", True),
            request_params.get("generate_dinner", True),
            request_params.get("generate_snacks", False)
        ])

        # Estimate ~400 tokens per recipe + overview
        estimated_tokens = (days * meals_per_day * 400) + 500
        max_tokens = min(estimated_tokens, self.max_tokens)  # Cap at configured max

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": max_tokens
        }

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 min timeout for large plans
                response = await client.post(
                    f"{self.api_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()

                data = response.json()
                plan_text = data["choices"][0]["message"]["content"]
                return plan_text

        except httpx.HTTPError as e:
            raise Exception(f"Error calling LLM API: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Unexpected LLM response format: {str(e)}")

    def build_prep_cook_prompt(
        self,
        inventory: Dict[str, Any],
        request_params: Dict[str, Any],
        dietary_profiles: List[Dict[str, str]],
        user_preferences: str = ""
    ) -> str:
        """Build the prompt for prep cook session generation."""
        num_meals = request_params.get("num_meals", 3)
        portions_per_meal = request_params.get("portions_per_meal", 4)
        protein_anchor = request_params.get("protein_anchor", "")
        calorie_target = request_params.get("calorie_target")
        unit_preference = request_params.get("unit_preference", "imperial")
        custom_persona = request_params.get("custom_persona", "You are a professional chef and nutritionist.")
        user_prompt = request_params.get("user_prompt", "")

        total_portions = num_meals * portions_per_meal
        unit_system = "imperial units (oz, lb, cups, tbsp, tsp)" if unit_preference == "imperial" else "metric units (g, kg, ml, l)"

        prompt_parts = [
            f"{custom_persona} You are planning a BATCH COOK SESSION — a single day of cooking that produces multiple freezer-ready meals.",
        ]

        if user_preferences:
            prompt_parts.extend([
                "",
                "USER PREFERENCES (take these into account for all suggestions):",
                user_preferences,
            ])

        prompt_parts.extend([
            "",
            "BATCH COOK PARAMETERS:",
            f"- Number of different meals: {num_meals}",
            f"- Portions per meal: {portions_per_meal}",
            f"- Total portions to produce: {total_portions}",
        ])

        if protein_anchor:
            prompt_parts.extend([
                "",
                f"SHARED PROTEIN ANCHOR: {protein_anchor}",
                "Divide this protein across multiple recipes. Show how much goes to each recipe.",
                "If there's not enough for all recipes, supplement with other proteins.",
            ])

        if calorie_target:
            prompt_parts.append(f"- Target calories per portion: ~{calorie_target}")

        # Equipment
        available_equipment = request_params.get("available_equipment", [])
        if available_equipment:
            prompt_parts.append("")
            prompt_parts.append("AVAILABLE KITCHEN EQUIPMENT:")
            for eq in available_equipment:
                prompt_parts.append(f"- {eq}")
            prompt_parts.append("Only use cooking methods that work with this equipment.")

        # Inventory
        use_inventory = request_params.get("use_inventory", True)
        if use_inventory and inventory.get("available_items"):
            prompt_parts.append("")
            prompt_parts.append("AVAILABLE INGREDIENTS (from pantry/fridge):")
            for item in inventory["available_items"][:50]:
                prompt_parts.append(f"- {item['name']}: {item['amount']} {item['unit']}")

            if request_params.get("prioritize_expiring") and inventory.get("expiring_soon"):
                prompt_parts.append("")
                prompt_parts.append("INGREDIENTS EXPIRING SOON (prioritize these!):")
                for item in inventory["expiring_soon"]:
                    prompt_parts.append(f"- {item['name']}: {item['amount']} (expires {item['expiry_date']})")

        # Dietary restrictions
        if dietary_profiles:
            prompt_parts.append("")
            prompt_parts.append("DIETARY RESTRICTIONS:")
            for profile in dietary_profiles:
                prompt_parts.append(f"- {profile['name']}: {profile['dietary_restrictions']}")

        if user_prompt:
            prompt_parts.append("")
            prompt_parts.append(f"ADDITIONAL NOTES: {user_prompt}")

        # Output format
        prompt_parts.extend([
            "",
            "IMPORTANT BATCH COOK REQUIREMENTS:",
            "- Every recipe MUST freeze well in individual portions",
            "- Include reheating instructions (microwave + oven, from frozen)",
            "- Include storage/portioning instructions",
            "- Think about efficiency: what can cook simultaneously?",
            "- Variety: different flavors, cuisines, and textures across meals",
            "",
            "OUTPUT FORMAT:",
            "Your response MUST have these sections in order:",
            "",
            "1. OVERVIEW — A brief paragraph summarizing the session: what you're making, total yield, estimated total cost.",
            "",
            "2. RECIPES — Each recipe uses this EXACT delimited format:",
            "",
            "===RECIPE===",
            "TITLE: [Recipe Name]",
            f"PORTIONS: {portions_per_meal}",
            "CALORIES: [estimated calories per portion]",
            "PREP_TIME: [active prep time in minutes for this recipe]",
            "ESTIMATED_COST: [total ingredient cost in USD, e.g. 12.50]",
            "",
            "**Ingredients:**",
            f"- [ingredient with quantity in {unit_system}]",
            "...",
            "",
            "**Instructions:**",
            "1. [step]",
            "...",
            "",
            "**Storage:** [How to portion and store]",
            "",
            "**Reheating:** [Microwave and oven instructions from frozen]",
            "===END_RECIPE===",
            "",
            "3. PREP DAY TIMELINE — A chronological schedule for cook day:",
            "===TIMELINE===",
            "[time] - [action] (for which recipe)",
            "[time] - [action]",
            "...",
            "===END_TIMELINE===",
            "",
            "4. SHOPPING LIST — Aggregated across all recipes, deduped and summed:",
            "===SHOPPING_LIST===",
            "PRODUCE:",
            "- [item]: [total quantity]",
            "PROTEINS:",
            "- [item]: [total quantity]",
            "DAIRY & REFRIGERATED:",
            "- [item]: [total quantity]",
            "PANTRY:",
            "- [item]: [total quantity]",
            "FROZEN:",
            "- [item]: [total quantity]",
            "===END_SHOPPING_LIST===",
            "",
            "CRITICAL RULES:",
            f"1. Generate exactly {num_meals} recipes",
            f"2. Each recipe yields {portions_per_meal} portions",
            "3. Every recipe MUST be between ===RECIPE=== and ===END_RECIPE===",
            "4. Include the TIMELINE between ===TIMELINE=== and ===END_TIMELINE===",
            "5. Include the SHOPPING LIST between ===SHOPPING_LIST=== and ===END_SHOPPING_LIST===",
            "6. Shopping list must aggregate across ALL recipes (don't list onions 3 times — sum them)",
        ])

        return "\n".join(prompt_parts)

    async def generate_prep_cook_session(
        self,
        inventory: Dict[str, Any],
        request_params: Dict[str, Any],
        dietary_profiles: List[Dict[str, str]],
        user_preferences: str = ""
    ) -> str:
        """Generate a prep cook session using the LLM. Returns raw text."""
        prompt = self.build_prep_cook_prompt(
            inventory, request_params, dietary_profiles, user_preferences
        )

        num_meals = request_params.get("num_meals", 3)
        estimated_tokens = (num_meals * 600) + 1500  # recipes + overview + timeline + shopping
        max_tokens = min(estimated_tokens, self.max_tokens)

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": max_tokens
        }

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.api_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            raise Exception(f"Error calling LLM API: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Unexpected LLM response format: {str(e)}")

    async def regenerate_meal_plan_recipe(
        self,
        day: int,
        meal_type: str,
        other_recipes: List[Dict[str, Any]],
        request_params: Dict[str, Any],
        dietary_profiles: List[Dict[str, str]],
        inventory: Dict[str, Any] = None,
        old_recipe_text: str = None,
        user_preferences: str = ""
    ) -> str:
        """
        Regenerate a single recipe from a meal plan with context about other recipes.

        Args:
            day: The day number for this recipe
            meal_type: Type of meal (breakfast, lunch, dinner, snack)
            other_recipes: List of other recipes in the plan (for ingredient context)
            request_params: Original meal plan generation parameters
            dietary_profiles: List of active dietary profiles
            inventory: Optional inventory data
            old_recipe_text: The recipe being replaced (so we can generate something different)

        Returns:
            Generated recipe text in the meal plan format
        """
        people = request_params.get("people", 2)
        budget_level = request_params.get("budget_level", "moderate")
        unit_preference = request_params.get("unit_preference", "imperial")
        custom_persona = request_params.get("custom_persona", "You are a professional chef and nutritionist.")

        # Effort level for this meal type
        effort_map = {
            "breakfast": request_params.get("breakfast_effort", 2),
            "lunch": request_params.get("lunch_effort", 2),
            "dinner": request_params.get("dinner_effort", 3),
            "snack": request_params.get("snack_effort", 1)
        }
        effort_level = effort_map.get(meal_type, 3)

        effort_descriptions = {
            1: "pre-packaged/minimal prep (microwave meals, sandwiches, ready-to-eat)",
            2: "quick and easy (15-20 min, simple cooking)",
            3: "moderate effort (30-45 min, standard cooking)",
            4: "involved (45-60 min, multiple components)",
            5: "high effort (60+ min, complex techniques)"
        }

        budget_descriptions = {
            "broke": "extremely tight budget - focus on the cheapest possible ingredients",
            "dirt_cheap": "very low budget - prioritize inexpensive staples",
            "cheap": "budget-conscious - use affordable ingredients",
            "moderate": "reasonable budget - balance cost and quality",
            "high": "comfortable budget - quality ingredients",
            "luxury": "no budget constraints - premium ingredients"
        }

        # Build context about other recipes and their ingredients
        other_ingredients = set()
        other_recipe_summaries = []
        for recipe in other_recipes:
            other_recipe_summaries.append(f"- Day {recipe.get('day')} {recipe.get('meal_type')}: {recipe.get('title')}")
            # Extract ingredients from recipe text (simple extraction)
            recipe_text = recipe.get('recipe_text', '')
            if '**Ingredients:**' in recipe_text:
                ingredients_section = recipe_text.split('**Ingredients:**')[1].split('**')[0]
                for line in ingredients_section.split('\n'):
                    line = line.strip()
                    if line.startswith('-'):
                        # Extract ingredient name (before the colon or quantity)
                        ingredient = line[1:].strip().split(':')[0].split(',')[0].strip()
                        if ingredient:
                            other_ingredients.add(ingredient.lower())

        unit_system = "imperial units (oz, lb, cups, tbsp, tsp)" if unit_preference == "imperial" else "metric units (g, kg, ml, l)"

        prompt_parts = [
            f"{custom_persona} Generate a SINGLE recipe to replace one in an existing meal plan.",
        ]

        if user_preferences:
            prompt_parts.extend([
                "",
                "USER PREFERENCES (take these into account for all suggestions):",
                user_preferences,
            ])

        prompt_parts.extend([
            "",
            f"RECIPE DETAILS:",
            f"- Day: {day}",
            f"- Meal type: {meal_type}",
            f"- Number of people: {people}",
            f"- Budget: {budget_level.upper()} - {budget_descriptions.get(budget_level, 'moderate budget')}",
            f"- Effort level: {effort_descriptions.get(effort_level, 'moderate')}",
            ""
        ])

        # Add the old recipe that's being replaced
        if old_recipe_text:
            prompt_parts.append("RECIPE BEING REPLACED (generate something DIFFERENT from this):")
            prompt_parts.append(old_recipe_text)
            prompt_parts.append("")

        # Add context about other recipes
        if other_recipe_summaries:
            prompt_parts.append("OTHER RECIPES IN THIS MEAL PLAN (for context - try to complement these):")
            prompt_parts.extend(other_recipe_summaries)
            prompt_parts.append("")

        # Add ingredients already being used
        if other_ingredients:
            prompt_parts.append("INGREDIENTS ALREADY BEING PURCHASED FOR OTHER RECIPES:")
            prompt_parts.append("(Consider reusing some of these to reduce shopping, but don't force it)")
            for ing in sorted(other_ingredients)[:30]:  # Limit to avoid token overflow
                prompt_parts.append(f"- {ing}")
            prompt_parts.append("")

        # Add inventory if available
        if inventory and inventory.get("available_items"):
            prompt_parts.append("AVAILABLE INGREDIENTS (from pantry/fridge):")
            for item in inventory["available_items"][:30]:
                prompt_parts.append(f"- {item['name']}: {item['amount']} {item['unit']}")
            prompt_parts.append("")

        # Add dietary restrictions
        if dietary_profiles:
            prompt_parts.append("DIETARY RESTRICTIONS:")
            for profile in dietary_profiles:
                prompt_parts.append(f"- {profile['name']}: {profile['dietary_restrictions']}")
            prompt_parts.append("")

        # Output format
        prompt_parts.extend([
            "OUTPUT FORMAT:",
            "Use this EXACT format:",
            "",
            "===RECIPE===",
            f"DAY: {day}",
            f"MEAL: {meal_type}",
            "TITLE: [Recipe Name]",
            "CALORIES: [estimated calories per serving]",
            "PREP_TIME: [time in minutes]",
            f"SERVINGS: {people}",
            "ESTIMATED_COST: [estimated total cost in USD, e.g. 8.50]",
            "",
            "**Ingredients:**",
            f"- [ingredient with quantity in {unit_system}]",
            "- [ingredient with quantity]",
            "...",
            "",
            "**Instructions:**",
            "1. [step]",
            "2. [step]",
            "...",
            "",
            "**Tips:** [optional quick tip]",
            "===END_RECIPE===",
            "",
            "Generate a DIFFERENT recipe than what was there before. Be creative!",
        ])

        prompt = "\n".join(prompt_parts)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.9,  # Higher for variety
            "max_tokens": 1500
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

