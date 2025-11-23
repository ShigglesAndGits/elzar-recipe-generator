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

