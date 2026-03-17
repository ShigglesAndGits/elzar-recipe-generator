import json
import re
import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from ..database import db
from ..services.grocy_client import GrocyClient
from ..services.llm_client import LLMClient
from ..utils.config_manager import get_effective_config

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None

class ChatSendRequest(BaseModel):
    session_id: Optional[int] = None  # None = create new session
    message: str
    # Session-level parameter overrides (collapsible header)
    cuisine: Optional[str] = None
    effort_level: Optional[str] = None
    servings: Optional[str] = None
    calories_per_serving: Optional[int] = None
    budget_level: Optional[str] = None
    available_equipment: List[str] = Field(default_factory=list)
    active_profiles: List[str] = Field(default_factory=list)
    elzar_voice: bool = False
    use_inventory: bool = True
    prioritize_expiring: bool = False

class ChatSendResponse(BaseModel):
    session_id: int
    session_name: str
    response: str  # The assistant's final text response
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)

class ChatSessionResponse(BaseModel):
    id: int
    name: str
    created_at: str
    updated_at: str

class ChatHistoryResponse(BaseModel):
    session: ChatSessionResponse
    messages: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function calling format)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "create_recipe",
            "description": "Generate a new recipe based on the conversation context and save it. Use this when the user wants you to create a specific recipe.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "What recipe to create — dish name, key constraints, any specifics from the conversation"
                    },
                    "servings": {"type": "string", "description": "Number of servings, e.g. '3-4'"},
                    "cuisine": {"type": "string", "description": "Cuisine type if specified"},
                },
                "required": ["description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_recipes",
            "description": "Search the user's recipe history by text, cuisine, or other filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text to search for in recipes"},
                    "cuisine": {"type": "string", "description": "Filter by cuisine type"},
                    "limit": {"type": "integer", "description": "Max results (default 10)"},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recipe",
            "description": "Get a specific recipe by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipe_id": {"type": "integer", "description": "The recipe ID"}
                },
                "required": ["recipe_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_ideas_list",
            "description": "Get the user's meal ideas list. Use this to see what they're brainstorming.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status_filter": {
                        "type": "string",
                        "enum": ["idea", "planned", "tested", "favorite"],
                        "description": "Filter by status"
                    },
                    "search": {"type": "string", "description": "Search text"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_ideas_list",
            "description": "Add a new idea to the brainstorm board.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Idea name"},
                    "notes": {"type": "string", "description": "Optional notes"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags like 'freezer-friendly', 'low-cal'"
                    },
                    "calorie_estimate": {"type": "string", "description": "e.g. '300-400'"},
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_idea",
            "description": "Update an existing idea (status, notes, tags, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "idea_id": {"type": "integer", "description": "The idea ID"},
                    "name": {"type": "string"},
                    "notes": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "status": {
                        "type": "string",
                        "enum": ["idea", "planned", "tested", "favorite"]
                    },
                    "calorie_estimate": {"type": "string"},
                },
                "required": ["idea_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_inventory",
            "description": "Check what's currently in the user's Grocy inventory (pantry/fridge). Only available when Grocy is configured.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {"type": "string", "description": "Optional: search for specific items"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_freezer",
            "description": "Check what's in the freezer. Only available when Grocy is configured.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_prep_cook_session",
            "description": "Generate a batch cook plan with multiple freezer-ready recipes, a prep day timeline, and an aggregated shopping list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "num_meals": {"type": "integer", "description": "Number of different meals (1-8)"},
                    "portions_per_meal": {"type": "integer", "description": "Portions per meal (1-20)"},
                    "protein_anchor": {"type": "string", "description": "Shared protein to build around, e.g. '5 lb chuck roast'"},
                    "calorie_target": {"type": "integer", "description": "Target calories per portion"},
                    "notes": {"type": "string", "description": "Additional instructions for the batch cook"},
                },
                "required": ["num_meals", "portions_per_meal"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_shopping_list",
            "description": "Generate an aggregated shopping list from one or more recipe IDs, grouped by store section.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipe_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Recipe IDs to aggregate"
                    }
                },
                "required": ["recipe_ids"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_recipe",
            "description": "Make targeted edits to an existing recipe while preserving the rest. If the recipe is locked, this will automatically create a variant instead of editing in place.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipe_id": {"type": "integer", "description": "The recipe ID to edit"},
                    "instructions": {"type": "string", "description": "What to change, e.g. 'swap chicken for tofu, add mushrooms'"},
                },
                "required": ["recipe_id", "instructions"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "copy_and_edit_recipe",
            "description": "Create a new recipe as a variant of an existing one, applying edits. Use this when the user wants to keep the original and create a modified version (e.g. 'make a vegetarian version of recipe 5').",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipe_id": {"type": "integer", "description": "The original recipe ID to fork from"},
                    "instructions": {"type": "string", "description": "What to change in the variant"},
                },
                "required": ["recipe_id", "instructions"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_preferences",
            "description": "Read the user's household preferences document.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_user_preferences",
            "description": "Update the user's household preferences. IMPORTANT: Always ASK the user before calling this — never silently update preferences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "new_content": {"type": "string", "description": "The updated preferences text (replaces the entire document)"},
                },
                "required": ["new_content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_debrief",
            "description": "Record a post-cooking debrief — what was cooked, what worked, what didn't, what was wasted. Use this when the user shares feedback about a meal or cooking session.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prep_session_id": {"type": "integer", "description": "Optional prep cook session ID this debrief is about"},
                    "what_was_cooked": {"type": "string", "description": "What the user actually cooked"},
                    "what_worked": {"type": "string", "description": "What went well — dishes that were hits, techniques that worked"},
                    "what_didnt_work": {"type": "string", "description": "What went wrong — dishes that flopped, ingredients that were off"},
                    "what_was_wasted": {"type": "string", "description": "What got thrown away or went unused"},
                    "notes": {"type": "string", "description": "Any other observations or preferences to remember"},
                },
                "required": ["what_was_cooked"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_debriefs",
            "description": "Retrieve recent post-cooking debriefs. Use this to learn from past cooking sessions when planning new ones.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of debriefs to retrieve (default 5)"},
                },
                "required": []
            }
        }
    },
]


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    config: Dict[str, Any],
    session_params: Dict[str, Any],
) -> str:
    """Execute a tool call and return the result as a string for the LLM."""

    grocy_configured = bool(config.get("grocy_url") and config.get("grocy_api_key"))

    try:
        if tool_name == "create_recipe":
            return await _tool_create_recipe(arguments, config, session_params)
        elif tool_name == "search_recipes":
            return await _tool_search_recipes(arguments)
        elif tool_name == "get_recipe":
            return await _tool_get_recipe(arguments)
        elif tool_name == "get_ideas_list":
            return await _tool_get_ideas_list(arguments)
        elif tool_name == "add_to_ideas_list":
            return await _tool_add_to_ideas_list(arguments)
        elif tool_name == "update_idea":
            return await _tool_update_idea(arguments)
        elif tool_name == "query_inventory":
            if not grocy_configured:
                return "Grocy is not configured. Inventory tracking is not available."
            return await _tool_query_inventory(arguments, config)
        elif tool_name == "query_freezer":
            if not grocy_configured:
                return "Grocy is not configured. Freezer tracking is not available."
            return await _tool_query_freezer(config)
        elif tool_name == "create_prep_cook_session":
            return await _tool_create_prep_cook_session(arguments, config, session_params)
        elif tool_name == "generate_shopping_list":
            return await _tool_generate_shopping_list(arguments, config)
        elif tool_name == "edit_recipe":
            return await _tool_edit_recipe(arguments, config)
        elif tool_name == "copy_and_edit_recipe":
            return await _tool_copy_and_edit_recipe(arguments, config)
        elif tool_name == "get_user_preferences":
            return await _tool_get_user_preferences()
        elif tool_name == "update_user_preferences":
            return await _tool_update_user_preferences(arguments)
        elif tool_name == "log_debrief":
            return await _tool_log_debrief(arguments)
        elif tool_name == "get_debriefs":
            return await _tool_get_debriefs(arguments)
        else:
            return f"Unknown tool: {tool_name}"
    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"


async def _tool_create_recipe(args: dict, config: dict, session_params: dict) -> str:
    """Generate a recipe via LLM and save it."""
    llm = LLMClient(
        config["llm_api_url"], config["llm_api_key"], config["llm_model"],
        max_tokens=int(config.get("llm_max_tokens", 16000))
    )

    # Build inventory
    inventory = {"available_items": [], "expiring_soon": []}
    grocy_configured = bool(config.get("grocy_url") and config.get("grocy_api_key"))
    if grocy_configured and session_params.get("use_inventory", True):
        try:
            grocy = GrocyClient(config["grocy_url"], config["grocy_api_key"])
            inventory = await grocy.format_inventory_for_llm(
                session_params.get("prioritize_expiring", False)
            )
        except Exception:
            pass

    # Get profiles
    dietary_profiles = []
    if session_params.get("active_profiles"):
        all_profiles = await db.get_all_profiles()
        dietary_profiles = [p for p in all_profiles if p["name"] in session_params["active_profiles"]]

    user_preferences = (await db.get_user_preferences()).get("content", "")

    request_params = {
        "cuisine": args.get("cuisine") or session_params.get("cuisine", "No Preference"),
        "time_minutes": 60,
        "effort_level": session_params.get("effort_level", "Medium"),
        "dish_preference": "I don't care",
        "calories_per_serving": session_params.get("calories_per_serving"),
        "use_external_ingredients": True,
        "prioritize_expiring": session_params.get("prioritize_expiring", False),
        "elzar_voice": session_params.get("elzar_voice", False),
        "servings": args.get("servings") or session_params.get("servings", "3-4"),
        "bulk_prep": False,
        "high_leftover_potential": False,
        "available_equipment": session_params.get("available_equipment", []),
        "user_prompt": args.get("description", ""),
        "unit_preference": config.get("unit_preference", "imperial"),
        "custom_persona": config.get("custom_persona", "You are a professional chef and nutritionist."),
    }

    recipe_text = await llm.generate_recipe(inventory, request_params, dietary_profiles, user_preferences)

    # Parse metadata from recipe text
    calories = None
    time_minutes = None
    estimated_cost = None
    cuisine = args.get("cuisine")

    metadata_match = re.search(r"METADATA:(.*?)---", recipe_text, re.DOTALL)
    if metadata_match:
        meta = metadata_match.group(1)
        cal_match = re.search(r"Calories:\s*(\d+)", meta)
        if cal_match:
            calories = int(cal_match.group(1))
        time_match = re.search(r"Total Time:\s*(\d+)", meta)
        if time_match:
            time_minutes = int(time_match.group(1))
        cost_match = re.search(r"Estimated Cost:\s*\$?([\d.]+)", meta)
        if cost_match:
            estimated_cost = float(cost_match.group(1))
        cuisine_match = re.search(r"Cuisine:\s*(.+)", meta)
        if cuisine_match:
            cuisine = cuisine_match.group(1).strip()

    recipe_id = await db.create_recipe({
        "recipe_text": recipe_text,
        "cuisine": cuisine,
        "time_minutes": time_minutes,
        "effort_level": session_params.get("effort_level"),
        "calories_per_serving": calories,
        "estimated_cost": estimated_cost,
        "used_external_ingredients": True,
        "prioritize_expiring": session_params.get("prioritize_expiring", False),
        "active_profiles": session_params.get("active_profiles", []),
        "user_prompt": args.get("description"),
        "llm_model": config["llm_model"],
    })

    return f"Recipe created (ID: {recipe_id}).\n\n{recipe_text}"


async def _tool_search_recipes(args: dict) -> str:
    filters = {}
    if args.get("query"):
        filters["search_text"] = args["query"]
    if args.get("cuisine"):
        filters["cuisine"] = args["cuisine"]
    limit = args.get("limit", 10)

    recipes = await db.get_recipes(limit=limit, filters=filters if filters else None)
    if not recipes:
        return "No recipes found matching your search."

    results = []
    for r in recipes:
        # Extract first line as title
        title = r["recipe_text"].split("\n")[0].strip("# ").strip("*").strip()[:80]
        meta = f"ID:{r['id']} | {r.get('cuisine', '?')} | {r.get('calories_per_serving', '?')} cal"
        if r.get("is_locked"):
            meta += " | 🔒"
        if r.get("is_saved"):
            meta += " | ⭐"
        results.append(f"- [{meta}] {title}")

    return f"Found {len(recipes)} recipe(s):\n" + "\n".join(results)


async def _tool_get_recipe(args: dict) -> str:
    recipe = await db.get_recipe(args["recipe_id"])
    if not recipe:
        return f"Recipe {args['recipe_id']} not found."
    return f"Recipe {recipe['id']} (locked={bool(recipe.get('is_locked'))}, saved={bool(recipe.get('is_saved'))}):\n\n{recipe['recipe_text']}"


async def _tool_get_ideas_list(args: dict) -> str:
    ideas = await db.get_ideas(
        status=args.get("status_filter"),
        search=args.get("search"),
    )
    if not ideas:
        return "No ideas found."

    results = []
    for idea in ideas:
        tags_raw = idea.get("tags", "[]")
        if isinstance(tags_raw, str):
            try:
                tags = json.loads(tags_raw)
            except json.JSONDecodeError:
                tags = []
        else:
            tags = tags_raw
        tag_str = f" [{', '.join(tags)}]" if tags else ""
        cal_str = f" ~{idea['calorie_estimate']} cal" if idea.get("calorie_estimate") else ""
        results.append(f"- ID:{idea['id']} [{idea['status']}] {idea['name']}{tag_str}{cal_str}")
        if idea.get("notes"):
            results.append(f"  Notes: {idea['notes'][:100]}")

    return f"{len(ideas)} idea(s):\n" + "\n".join(results)


async def _tool_add_to_ideas_list(args: dict) -> str:
    idea_id = await db.create_idea({
        "name": args["name"],
        "notes": args.get("notes", ""),
        "tags": args.get("tags", []),
        "calorie_estimate": args.get("calorie_estimate"),
        "status": "idea",
    })
    return f"Added idea '{args['name']}' (ID: {idea_id})"


async def _tool_update_idea(args: dict) -> str:
    idea_id = args.pop("idea_id")
    if not args:
        return "No fields to update."
    success = await db.update_idea(idea_id, args)
    if not success:
        return f"Idea {idea_id} not found."
    return f"Updated idea {idea_id}"


async def _tool_query_inventory(args: dict, config: dict) -> str:
    grocy = GrocyClient(config["grocy_url"], config["grocy_api_key"])
    inventory = await grocy.format_inventory_for_llm(False)
    items = inventory.get("available_items", [])

    search = args.get("search", "").lower()
    if search:
        items = [i for i in items if search in i["name"].lower()]

    if not items:
        return "No items found in inventory." if search else "Inventory is empty."

    lines = [f"- {i['name']}: {i['amount']} {i['unit']}" for i in items[:50]]
    return f"{len(items)} item(s) in stock:\n" + "\n".join(lines)


async def _tool_query_freezer(config: dict) -> str:
    grocy = GrocyClient(config["grocy_url"], config["grocy_api_key"])
    data = await grocy.get_freezer_stock()
    items = data.get("items", [])
    if not items:
        return "Freezer is empty."

    lines = []
    for i in items:
        line = f"- {i['product_name']}: {i['amount']} {i['unit']}"
        if i.get("best_before_date"):
            line += f" (exp: {i['best_before_date']})"
        if i.get("earliest_purchased"):
            line += f" (frozen: {i['earliest_purchased']})"
        lines.append(line)

    return f"{len(items)} item(s) in freezer:\n" + "\n".join(lines)


async def _tool_create_prep_cook_session(args: dict, config: dict, session_params: dict) -> str:
    """Delegate to the prep cook generation endpoint logic."""
    from .prepcook import parse_prep_cook_response, get_user_preferences_text

    llm = LLMClient(
        config["llm_api_url"], config["llm_api_key"], config["llm_model"],
        max_tokens=int(config.get("llm_max_tokens", 16000))
    )

    inventory = {"available_items": [], "expiring_soon": []}
    grocy_configured = bool(config.get("grocy_url") and config.get("grocy_api_key"))
    if grocy_configured and session_params.get("use_inventory", True):
        try:
            grocy = GrocyClient(config["grocy_url"], config["grocy_api_key"])
            inventory = await grocy.format_inventory_for_llm(
                session_params.get("prioritize_expiring", False)
            )
        except Exception:
            pass

    dietary_profiles = []
    if session_params.get("active_profiles"):
        all_profiles = await db.get_all_profiles()
        dietary_profiles = [p for p in all_profiles if p["name"] in session_params["active_profiles"]]

    user_preferences = await get_user_preferences_text()

    request_params = {
        "num_meals": args.get("num_meals", 3),
        "portions_per_meal": args.get("portions_per_meal", 4),
        "protein_anchor": args.get("protein_anchor", ""),
        "calorie_target": args.get("calorie_target"),
        "available_equipment": session_params.get("available_equipment", []),
        "use_inventory": session_params.get("use_inventory", True),
        "prioritize_expiring": session_params.get("prioritize_expiring", False),
        "user_prompt": args.get("notes", ""),
        "unit_preference": config.get("unit_preference", "imperial"),
        "custom_persona": config.get("custom_persona", "You are a professional chef and nutritionist."),
    }

    raw_text = await llm.generate_prep_cook_session(
        inventory, request_params, dietary_profiles, user_preferences
    )

    parsed = parse_prep_cook_response(raw_text, args.get("portions_per_meal", 4))

    # Save to DB
    db_recipes = []
    for recipe in parsed["recipes"]:
        db_recipes.append({
            "recipe_text": recipe["recipe_text"],
            "cuisine": None,
            "time_minutes": recipe.get("time_minutes"),
            "effort_level": None,
            "calories_per_serving": recipe.get("calories_per_serving"),
            "estimated_cost": recipe.get("estimated_cost"),
        })

    session_data = {
        "num_meals": args.get("num_meals", 3),
        "portions_per_meal": args.get("portions_per_meal", 4),
        "protein_anchor": args.get("protein_anchor"),
        "calorie_target": args.get("calorie_target"),
        "equipment": session_params.get("available_equipment", []),
        "active_profiles": session_params.get("active_profiles", []),
        "user_prompt": args.get("notes"),
        "overview": parsed["overview"],
        "timeline": parsed["timeline"],
        "shopping_list": parsed["shopping_list"],
        "llm_model": config["llm_model"],
    }

    session_id = await db.create_prep_cook_session(session_data, db_recipes)

    # Build summary
    recipe_list = "\n".join(
        f"- {r.get('title', 'Untitled')} ({r.get('calories_per_serving', '?')} cal/portion, est ${r.get('estimated_cost', '?')})"
        for r in parsed["recipes"]
    )

    result = f"Prep cook session created (ID: {session_id})!\n\n"
    result += f"**Overview:** {parsed['overview']}\n\n"
    result += f"**Recipes:**\n{recipe_list}\n\n"
    if parsed["timeline"]:
        result += f"**Prep Day Timeline:**\n{parsed['timeline']}\n\n"
    if parsed["shopping_list"]:
        result += f"**Shopping List:**\n{parsed['shopping_list']}"

    return result


async def _tool_generate_shopping_list(args: dict, config: dict) -> str:
    """Generate aggregated shopping list from recipe IDs using LLM."""
    recipe_ids = args.get("recipe_ids", [])
    if not recipe_ids:
        return "No recipe IDs provided."

    recipes = []
    for rid in recipe_ids:
        recipe = await db.get_recipe(rid)
        if recipe:
            recipes.append(recipe)

    if not recipes:
        return "None of the provided recipe IDs were found."

    # Build combined ingredient text
    combined = "Generate an aggregated shopping list from these recipes. Combine duplicate ingredients and sum their quantities.\n\n"
    for r in recipes:
        title = r["recipe_text"].split("\n")[0].strip("# ").strip("*").strip()[:80]
        combined += f"--- {title} (ID:{r['id']}) ---\n{r['recipe_text']}\n\n"

    combined += """Group items by store section:
PRODUCE & REFRIGERATED:
PROTEINS:
DAIRY:
PANTRY:
FROZEN:

Format as a clean plain-text list optimized for copy/paste into a text message. Sum quantities for duplicate items across recipes."""

    # Check Grocy inventory to mark what's already on hand
    grocy_configured = bool(config.get("grocy_url") and config.get("grocy_api_key"))
    if grocy_configured:
        try:
            grocy = GrocyClient(config["grocy_url"], config["grocy_api_key"])
            inventory = await grocy.format_inventory_for_llm(False)
            if inventory.get("available_items"):
                combined += "\n\nALREADY ON HAND (subtract these and add an 'ALREADY HAVE' section):\n"
                for item in inventory["available_items"][:40]:
                    combined += f"- {item['name']}: {item['amount']} {item['unit']}\n"
        except Exception:
            pass

    llm = LLMClient(
        config["llm_api_url"], config["llm_api_key"], config["llm_model"],
        max_tokens=int(config.get("llm_max_tokens", 16000))
    )

    payload = {
        "model": llm.model,
        "messages": [{"role": "user", "content": combined}],
        "temperature": 0.3,
        "max_tokens": 2000,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{llm.api_url}/chat/completions",
            headers=llm.headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def _tool_edit_recipe(args: dict, config: dict) -> str:
    """Apply targeted edits to a recipe."""
    recipe = await db.get_recipe(args["recipe_id"])
    if not recipe:
        return f"Recipe {args['recipe_id']} not found."

    is_locked = bool(recipe.get("is_locked"))
    action = "creating a variant of" if is_locked else "editing"

    llm = LLMClient(
        config["llm_api_url"], config["llm_api_key"], config["llm_model"],
        max_tokens=int(config.get("llm_max_tokens", 16000))
    )

    prompt = f"""Apply the following edits to this recipe. Preserve everything that isn't being changed.

ORIGINAL RECIPE:
{recipe['recipe_text']}

EDITS REQUESTED:
{args['instructions']}

Return the COMPLETE updated recipe text (not just the changes). Keep the same format."""

    payload = {
        "model": llm.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": min(4000, int(config.get("llm_max_tokens", 16000))),
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{llm.api_url}/chat/completions",
            headers=llm.headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        edited_text = data["choices"][0]["message"]["content"]

    if is_locked:
        # Create a variant instead of editing
        new_id = await _create_recipe_variant(recipe, edited_text, args, config)
        return f"Recipe {args['recipe_id']} is locked — created variant (ID: {new_id}) instead.\n\n{edited_text}"
    else:
        # Update in place
        import aiosqlite
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute(
                "UPDATE recipes SET recipe_text = ?, last_edited = CURRENT_TIMESTAMP WHERE id = ?",
                (edited_text, args["recipe_id"])
            )
            await conn.commit()
        return f"Recipe {args['recipe_id']} updated.\n\n{edited_text}"


async def _create_recipe_variant(original: dict, new_text: str, args: dict, config: dict) -> int:
    """Create a new recipe as a variant of an existing one."""
    new_id = await db.create_recipe({
        "recipe_text": new_text,
        "cuisine": original.get("cuisine"),
        "time_minutes": original.get("time_minutes"),
        "effort_level": original.get("effort_level"),
        "calories_per_serving": original.get("calories_per_serving"),
        "estimated_cost": original.get("estimated_cost"),
        "used_external_ingredients": original.get("used_external_ingredients"),
        "prioritize_expiring": original.get("prioritize_expiring"),
        "active_profiles": json.loads(original.get("active_profiles", "[]")),
        "user_prompt": args.get("instructions", ""),
        "llm_model": config["llm_model"],
    })
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        await conn.execute(
            "UPDATE recipes SET parent_recipe_id = ? WHERE id = ?",
            (original["id"], new_id)
        )
        await conn.commit()
    return new_id


async def _tool_copy_and_edit_recipe(args: dict, config: dict) -> str:
    """Fork a recipe as a new variant and apply edits."""
    recipe = await db.get_recipe(args["recipe_id"])
    if not recipe:
        return f"Recipe {args['recipe_id']} not found."

    llm = LLMClient(
        config["llm_api_url"], config["llm_api_key"], config["llm_model"],
        max_tokens=int(config.get("llm_max_tokens", 16000))
    )

    prompt = f"""Apply the following edits to this recipe. Preserve everything that isn't being changed.

ORIGINAL RECIPE:
{recipe['recipe_text']}

EDITS REQUESTED:
{args['instructions']}

Return the COMPLETE updated recipe text (not just the changes). Keep the same format."""

    payload = {
        "model": llm.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": min(4000, int(config.get("llm_max_tokens", 16000))),
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{llm.api_url}/chat/completions",
            headers=llm.headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        edited_text = data["choices"][0]["message"]["content"]

    new_id = await _create_recipe_variant(recipe, edited_text, args, config)
    return f"Created variant of recipe {args['recipe_id']} (new ID: {new_id}).\n\n{edited_text}"


async def _tool_get_user_preferences() -> str:
    prefs = await db.get_user_preferences()
    content = prefs.get("content", "")
    if not content:
        return "No household preferences set."
    return f"Current household preferences:\n\n{content}"


async def _tool_update_user_preferences(args: dict) -> str:
    await db.set_user_preferences(args["new_content"])
    return "Household preferences updated."


async def _tool_log_debrief(args: dict) -> str:
    debrief_id = await db.create_debrief(args)
    parts = [f"Debrief #{debrief_id} recorded."]
    if args.get("what_worked"):
        parts.append(f"What worked: {args['what_worked']}")
    if args.get("what_didnt_work"):
        parts.append(f"What didn't work: {args['what_didnt_work']}")
    if args.get("what_was_wasted"):
        parts.append(f"Wasted: {args['what_was_wasted']}")
    return " | ".join(parts)


async def _tool_get_debriefs(args: dict) -> str:
    limit = args.get("limit", 5)
    debriefs = await db.get_debriefs(limit=limit)
    if not debriefs:
        return "No debriefs recorded yet."

    lines = [f"Recent debriefs ({len(debriefs)}):"]
    for d in debriefs:
        lines.append(f"\n--- Debrief #{d['id']} ({d['created_at']}) ---")
        if d.get("what_was_cooked"):
            lines.append(f"Cooked: {d['what_was_cooked']}")
        if d.get("what_worked"):
            lines.append(f"Worked: {d['what_worked']}")
        if d.get("what_didnt_work"):
            lines.append(f"Didn't work: {d['what_didnt_work']}")
        if d.get("what_was_wasted"):
            lines.append(f"Wasted: {d['what_was_wasted']}")
        if d.get("notes"):
            lines.append(f"Notes: {d['notes']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

async def build_system_prompt(
    config: Dict[str, Any],
    session_params: Dict[str, Any],
) -> str:
    """Build the system prompt with all context."""
    parts = []

    # Persona
    custom_persona = config.get("custom_persona", "You are a professional chef and nutritionist.")
    parts.append(custom_persona)

    # Elzar voice
    if session_params.get("elzar_voice"):
        parts.append(
            "You deliver your responses in the voice of Elzar, the TV chef from Futurama. "
            "Use 'BAM!' once or twice, maybe mention 'Kick it up a notch' or 'Spice Weasel' sparingly. "
            "Keep it fun but don't overdo it."
        )

    parts.append("")
    parts.append(
        "You are a conversational meal planning assistant. Help the user brainstorm meals, "
        "plan batch cooks, manage their ideas list, and generate recipes through natural conversation. "
        "You have access to tool calls to take real actions."
    )

    # User preferences
    prefs = await db.get_user_preferences()
    pref_content = prefs.get("content", "")
    if pref_content:
        parts.extend([
            "",
            "HOUSEHOLD PREFERENCES (always consider these):",
            pref_content,
        ])

    # Session parameters (from collapsible header)
    param_parts = []
    if session_params.get("cuisine") and session_params["cuisine"] != "No Preference":
        param_parts.append(f"Preferred cuisine: {session_params['cuisine']}")
    if session_params.get("effort_level"):
        param_parts.append(f"Effort level: {session_params['effort_level']}")
    if session_params.get("servings"):
        param_parts.append(f"Default servings: {session_params['servings']}")
    if session_params.get("calories_per_serving"):
        param_parts.append(f"Target calories/serving: {session_params['calories_per_serving']}")
    if session_params.get("budget_level"):
        param_parts.append(f"Budget: {session_params['budget_level']}")
    if session_params.get("available_equipment"):
        param_parts.append(f"Available equipment: {', '.join(session_params['available_equipment'])}")

    if param_parts:
        parts.extend([
            "",
            "SESSION DEFAULTS (user's current settings — use as defaults for any recipes, "
            "but the user can override via conversation):",
        ] + param_parts)

    # Dietary profiles
    if session_params.get("active_profiles"):
        all_profiles = await db.get_all_profiles()
        active = [p for p in all_profiles if p["name"] in session_params["active_profiles"]]
        if active:
            parts.extend(["", "ACTIVE DIETARY PROFILES:"])
            for p in active:
                parts.append(f"- {p['name']}: {p['dietary_restrictions']}")

    # Grocy status
    grocy_configured = bool(config.get("grocy_url") and config.get("grocy_api_key"))
    if not grocy_configured:
        parts.extend([
            "",
            "NOTE: Grocy inventory is NOT configured. Do not offer to check inventory or "
            "freezer stock. The query_inventory and query_freezer tools are unavailable.",
        ])

    # Recent debriefs (feedback loop)
    recent_debriefs = await db.get_debriefs(limit=3)
    if recent_debriefs:
        parts.extend(["", "RECENT COOKING FEEDBACK (consider when planning):"])
        for d in recent_debriefs:
            summary = []
            if d.get("what_was_cooked"):
                summary.append(f"Cooked: {d['what_was_cooked']}")
            if d.get("what_worked"):
                summary.append(f"Liked: {d['what_worked']}")
            if d.get("what_didnt_work"):
                summary.append(f"Didn't work: {d['what_didnt_work']}")
            if d.get("what_was_wasted"):
                summary.append(f"Wasted: {d['what_was_wasted']}")
            parts.append(f"- [{d['created_at'][:10]}] {'; '.join(summary)}")

    # Behavioral rules
    parts.extend([
        "",
        "IMPORTANT RULES:",
        "- When creating recipes, use the create_recipe tool — don't just write a recipe in chat text.",
        "- When the user mentions a preference or opinion worth remembering (e.g. 'I hate cilantro'), "
        "  ASK them if they'd like you to save it to their preferences before calling update_user_preferences. "
        "  Never silently update preferences.",
        "- When the user asks about what's in the fridge/pantry/freezer, use the query tools.",
        "- Keep responses concise. Don't repeat the full recipe back in chat — just confirm it was created "
        "  and highlight key details.",
        "- You can call multiple tools in one turn if needed.",
        "- When suggesting recipes or planning meals, proactively point out ingredients that "
        "  could be prepped in bulk and frozen for future use — things like caramelized onions, "
        "  minced garlic, herb butters, cooked grains, blanched vegetables, homemade stock, "
        "  spice blends, etc. If the user is already making something that involves a bulk-prep "
        "  opportunity (e.g. caramelizing onions for a recipe), suggest making extra to freeze.",
    ])

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Chat endpoint — the main loop
# ---------------------------------------------------------------------------

def _filter_tools_for_config(config: Dict[str, Any]) -> List[dict]:
    """Remove Grocy-dependent tools when Grocy isn't configured."""
    grocy_configured = bool(config.get("grocy_url") and config.get("grocy_api_key"))
    if grocy_configured:
        return TOOL_DEFINITIONS

    grocy_tools = {"query_inventory", "query_freezer"}
    return [t for t in TOOL_DEFINITIONS if t["function"]["name"] not in grocy_tools]


@router.post("/send", response_model=ChatSendResponse)
async def send_message(request: ChatSendRequest):
    """
    Send a message and get a response. Handles the full tool call loop.
    Creates a new session if session_id is None.
    """
    config = await get_effective_config()

    # Create or verify session
    if request.session_id is None:
        session_id = await db.create_chat_session()
        # Auto-name from first message
        name = request.message[:50].strip()
        if len(request.message) > 50:
            name += "..."
        await db.update_chat_session_name(session_id, name)
    else:
        session = await db.get_chat_session(request.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        session_id = request.session_id

    # Build session params from request
    session_params = {
        "cuisine": request.cuisine,
        "effort_level": request.effort_level,
        "servings": request.servings,
        "calories_per_serving": request.calories_per_serving,
        "budget_level": request.budget_level,
        "available_equipment": request.available_equipment,
        "active_profiles": request.active_profiles,
        "elzar_voice": request.elzar_voice,
        "use_inventory": request.use_inventory,
        "prioritize_expiring": request.prioritize_expiring,
    }

    # Build system prompt
    system_prompt = await build_system_prompt(config, session_params)

    # Save user message
    await db.add_chat_message(session_id, {
        "role": "user",
        "content": request.message,
    })

    # Load message history
    db_messages = await db.get_chat_messages(session_id)

    # Convert to OpenAI format
    messages = [{"role": "system", "content": system_prompt}]
    for msg in db_messages:
        entry = {"role": msg["role"]}
        if msg.get("content"):
            entry["content"] = msg["content"]
        if msg.get("tool_calls"):
            entry["tool_calls"] = msg["tool_calls"]
        if msg.get("tool_call_id"):
            entry["tool_call_id"] = msg["tool_call_id"]
        if msg.get("name"):
            entry["name"] = msg["name"]
        messages.append(entry)

    # Tool call loop
    tools = _filter_tools_for_config(config)
    tool_results = []
    max_iterations = 5  # Safety limit

    for _ in range(max_iterations):
        payload = {
            "model": config["llm_model"],
            "messages": messages,
            "tools": tools,
            "temperature": 0.7,
            "max_tokens": int(config.get("llm_max_tokens", 16000)),
        }

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{config['llm_api_url']}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config['llm_api_key']}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"LLM API error: {str(e)}",
            )

        choice = data["choices"][0]
        assistant_msg = choice["message"]
        finish_reason = choice.get("finish_reason", "stop")

        # Check for tool calls
        if assistant_msg.get("tool_calls"):
            # Save assistant message with tool calls
            await db.add_chat_message(session_id, {
                "role": "assistant",
                "content": assistant_msg.get("content"),
                "tool_calls": assistant_msg["tool_calls"],
            })
            messages.append(assistant_msg)

            # Execute each tool call
            for tc in assistant_msg["tool_calls"]:
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    fn_args = {}

                print(f"🔧 Executing tool: {fn_name}({fn_args})")
                result = await execute_tool(fn_name, fn_args, config, session_params)

                tool_results.append({
                    "tool": fn_name,
                    "args": fn_args,
                    "result_preview": result[:200] if result else "",
                })

                # Save tool result message
                tool_msg = {
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tc["id"],
                    "name": fn_name,
                }
                await db.add_chat_message(session_id, tool_msg)
                messages.append(tool_msg)

            # Continue the loop — LLM needs to process tool results
            continue

        else:
            # No tool calls — we have the final response
            final_content = assistant_msg.get("content", "")

            await db.add_chat_message(session_id, {
                "role": "assistant",
                "content": final_content,
            })

            session = await db.get_chat_session(session_id)

            return ChatSendResponse(
                session_id=session_id,
                session_name=session["name"] if session else "Chat",
                response=final_content,
                tool_results=tool_results,
            )

    # If we hit max iterations, return what we have
    return ChatSendResponse(
        session_id=session_id,
        session_name="Chat",
        response="I ran into a loop processing your request. Please try rephrasing.",
        tool_results=tool_results,
    )


# ---------------------------------------------------------------------------
# Session management endpoints
# ---------------------------------------------------------------------------

@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_sessions(limit: int = 50):
    """Get recent chat sessions."""
    sessions = await db.get_chat_sessions(limit)
    return [
        ChatSessionResponse(
            id=s["id"],
            name=s["name"],
            created_at=str(s["created_at"]),
            updated_at=str(s["updated_at"]),
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=ChatHistoryResponse)
async def get_session_history(session_id: int):
    """Get a chat session with full message history."""
    session = await db.get_chat_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    messages = await db.get_chat_messages(session_id)

    # Filter to user-facing messages only (exclude tool internals for display)
    display_messages = []
    for msg in messages:
        display_messages.append({
            "id": msg["id"],
            "role": msg["role"],
            "content": msg.get("content"),
            "tool_calls": msg.get("tool_calls"),
            "tool_call_id": msg.get("tool_call_id"),
            "name": msg.get("name"),
            "created_at": str(msg["created_at"]),
        })

    return ChatHistoryResponse(
        session=ChatSessionResponse(
            id=session["id"],
            name=session["name"],
            created_at=str(session["created_at"]),
            updated_at=str(session["updated_at"]),
        ),
        messages=display_messages,
    )


@router.put("/sessions/{session_id}/name")
async def rename_session(session_id: int, body: dict):
    """Rename a chat session."""
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    success = await db.update_chat_session_name(session_id, name)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success"}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: int):
    """Delete a chat session and all its messages."""
    success = await db.delete_chat_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success", "message": "Session deleted"}
