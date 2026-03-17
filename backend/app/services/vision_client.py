import httpx
import base64
import json
from typing import List, Dict, Any, Optional
from pathlib import Path


class VisionClient:
    """
    Vision-capable LLM client for analyzing pantry/fridge images
    and extracting food items for inventory management.
    """

    def __init__(self, api_url: str, api_key: str, model: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def _encode_image(self, image_data: bytes, media_type: str = "image/jpeg") -> str:
        """Encode image bytes to base64 string"""
        return base64.b64encode(image_data).decode("utf-8")

    def _build_scan_prompt(
        self,
        grocy_products: List[Dict[str, Any]],
        grocy_locations: List[Dict[str, Any]],
        unit_preference: str = "metric"
    ) -> str:
        """Build the system prompt for pantry scanning"""

        # Format products for context
        product_list = "\n".join([
            f"- ID: {p['id']}, Name: {p['name']}"
            for p in grocy_products[:200]  # Limit to avoid token overflow
        ])

        # Format locations
        location_list = "\n".join([
            f"- ID: {loc['id']}, Name: {loc['name']}"
            for loc in grocy_locations
        ])

        unit_guidance = (
            "Use metric units (g, kg, ml, l) for quantities."
            if unit_preference == "metric"
            else "Use imperial units (oz, lb, fl oz, gal) for quantities."
        )

        return f"""You are a pantry inventory assistant with computer vision capabilities. Analyze the image(s) of a pantry, refrigerator, or food storage area and identify all visible food items.

AVAILABLE GROCY PRODUCTS (match to these when possible):
{product_list}

AVAILABLE STORAGE LOCATIONS:
{location_list}

TASK:
Look at the image(s) carefully and identify every food item you can see. For each item:

1. **Identify the item** - What food/ingredient is it?
2. **Estimate quantity** - How much is there? (count for discrete items, weight/volume for bulk)
3. **Determine unit** - {unit_guidance}
4. **Match to Grocy product** - If you see "Heinz Ketchup", match to "Ketchup" in Grocy
5. **Assign location** - Based on where the photo was taken (Fridge for cold items, Pantry for shelf-stable)
6. **Rate confidence**:
   - "high": Item is clearly visible and identifiable
   - "medium": Item is partially visible or label is hard to read
   - "low": Item is obscured or uncertain identification
   - "new": Item not found in Grocy product list

IMPORTANT GUIDELINES:
- **Be thorough** - List EVERY food item you can see, even partially visible ones
- **Be specific** - "Organic whole milk" not just "milk", "Granny Smith apples" not just "apples"
- **Estimate reasonably** - A gallon jug is ~3.78L, a standard can is ~400g, etc.
- **Match generically** - "Barilla Spaghetti" matches "Pasta" or "Spaghetti"
- **Skip non-food items** - Don't list cleaning supplies, containers, etc.
- **Note expiration dates** if visible on packages

EXAMPLES OF GOOD IDENTIFICATIONS:
- Carton of eggs (visible: 12 count) → 12 count eggs
- Gallon of 2% milk → 1 gallon (or 3.78L) milk
- Bag of flour (5lb bag, appears half full) → 2.5 lb flour
- Stack of yogurt cups (6 visible) → 6 count yogurt
- Jar of peanut butter (mostly full) → 1 jar (~16oz) peanut butter

Return ONLY a valid JSON array with NO additional text or explanation:
[
  {{
    "original_text": "Gallon jug of 2% milk",
    "item_name": "Milk",
    "quantity": 3.78,
    "unit": "l",
    "matched_product_id": 5,
    "matched_product_name": "Milk",
    "confidence": "high",
    "suggested_location_id": 1,
    "suggested_location_name": "Fridge",
    "notes": "2% reduced fat, expires 12/15"
  }}
]

If you cannot identify any food items in the image, return an empty array: []"""

    async def scan_image(
        self,
        image_data: bytes,
        media_type: str,
        grocy_products: List[Dict[str, Any]],
        grocy_locations: List[Dict[str, Any]],
        unit_preference: str = "metric"
    ) -> List[Dict[str, Any]]:
        """
        Scan a single image and extract food items.

        Args:
            image_data: Raw image bytes
            media_type: MIME type (image/jpeg, image/png, etc.)
            grocy_products: List of existing Grocy products for matching
            grocy_locations: List of storage locations
            unit_preference: "metric" or "imperial"

        Returns:
            List of parsed items matching the inventory format
        """
        return await self.scan_images(
            [(image_data, media_type)],
            grocy_products,
            grocy_locations,
            unit_preference
        )

    async def scan_images(
        self,
        images: List[tuple[bytes, str]],  # List of (image_data, media_type)
        grocy_products: List[Dict[str, Any]],
        grocy_locations: List[Dict[str, Any]],
        unit_preference: str = "metric"
    ) -> List[Dict[str, Any]]:
        """
        Scan multiple images and extract food items from all of them.

        Args:
            images: List of (image_data, media_type) tuples
            grocy_products: List of existing Grocy products for matching
            grocy_locations: List of storage locations
            unit_preference: "metric" or "imperial"

        Returns:
            Combined list of parsed items from all images
        """
        prompt = self._build_scan_prompt(grocy_products, grocy_locations, unit_preference)

        # Build the content array with text and images
        content = [
            {
                "type": "text",
                "text": prompt
            }
        ]

        # Add each image
        for image_data, media_type in images:
            base64_image = self._encode_image(image_data, media_type)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{base64_image}"
                }
            })

        # Add instruction for multiple images
        if len(images) > 1:
            content.append({
                "type": "text",
                "text": f"I've provided {len(images)} images. Please analyze ALL of them and combine the results into a single list. Avoid duplicates if the same item appears in multiple photos."
            })

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "temperature": 0.3,  # Lower temperature for more consistent parsing
            "max_tokens": 4000
        }

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:  # Longer timeout for vision
                response = await client.post(
                    f"{self.api_url}/chat/completions",
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

                # Normalize the response format to match inventory expectations
                normalized_items = []
                for item in parsed_items:
                    normalized_items.append({
                        "original_text": item.get("original_text", item.get("item_name", "")),
                        "item_name": item.get("item_name", ""),
                        "quantity": item.get("quantity", 1),
                        "unit": item.get("unit", "count"),
                        "matched_product_id": item.get("matched_product_id"),
                        "matched_product_name": item.get("matched_product_name"),
                        "confidence": item.get("confidence", "medium"),
                        "suggested_location_id": item.get("suggested_location_id"),
                        "suggested_location_name": item.get("suggested_location_name"),
                        "notes": item.get("notes", "")
                    })

                return normalized_items

        except httpx.HTTPError as e:
            raise Exception(f"Error calling Vision API: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Error parsing Vision API response as JSON: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Unexpected Vision API response format: {str(e)}")
