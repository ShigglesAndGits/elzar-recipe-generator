import aiosqlite
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path


class Database:
    """SQLite database handler for Elzar"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        # Ensure the directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def init_db(self):
        """Initialize database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Recipes table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS recipes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    recipe_text TEXT NOT NULL,
                    cuisine TEXT,
                    time_minutes INTEGER,
                    effort_level TEXT,
                    dish_preference TEXT,
                    calories_per_serving INTEGER,
                    estimated_cost REAL,
                    used_external_ingredients BOOLEAN,
                    prioritize_expiring BOOLEAN,
                    active_profiles TEXT,
                    grocy_inventory_snapshot TEXT,
                    user_prompt TEXT,
                    llm_model TEXT
                )
            """)

            # Add estimated_cost column if it doesn't exist (migration for existing DBs)
            try:
                await db.execute("ALTER TABLE recipes ADD COLUMN estimated_cost REAL")
            except Exception:
                pass  # Column already exists

            # Recipe locking & saving migrations
            for col, col_def in [
                ("is_locked", "BOOLEAN DEFAULT 0"),
                ("is_saved", "BOOLEAN DEFAULT 0"),
                ("tags", "TEXT DEFAULT '[]'"),
                ("parent_recipe_id", "INTEGER"),
            ]:
                try:
                    await db.execute(f"ALTER TABLE recipes ADD COLUMN {col} {col_def}")
                except Exception:
                    pass  # Column already exists

            # Settings table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Dietary profiles table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS dietary_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    dietary_restrictions TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_recipes_created_at 
                ON recipes(created_at DESC)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_recipes_cuisine 
                ON recipes(cuisine)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_recipes_time 
                ON recipes(time_minutes)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_recipes_calories 
                ON recipes(calories_per_serving)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_profiles_name
                ON dietary_profiles(name)
            """)

            # User preferences table (single document)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    content TEXT NOT NULL DEFAULT '',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Ensure the single row exists
            await db.execute("""
                INSERT OR IGNORE INTO user_preferences (id, content) VALUES (1, '')
            """)

            # Meal plans table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS meal_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    overview TEXT,
                    total_days INTEGER,
                    total_people INTEGER,
                    budget_level TEXT,
                    daily_calorie_target INTEGER,
                    active_profiles TEXT,
                    request_params TEXT,
                    llm_model TEXT
                )
            """)

            # Meal plan recipes table (individual recipes within a plan)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS meal_plan_recipes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meal_plan_id INTEGER NOT NULL,
                    day INTEGER NOT NULL,
                    meal_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    recipe_text TEXT NOT NULL,
                    calories_estimate INTEGER,
                    prep_time_minutes INTEGER,
                    servings INTEGER DEFAULT 2,
                    estimated_cost REAL,
                    FOREIGN KEY (meal_plan_id) REFERENCES meal_plans(id) ON DELETE CASCADE
                )
            """)

            # Add estimated_cost column to meal_plan_recipes if it doesn't exist
            try:
                await db.execute("ALTER TABLE meal_plan_recipes ADD COLUMN estimated_cost REAL")
            except Exception:
                pass  # Column already exists

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_meal_plans_created_at
                ON meal_plans(created_at DESC)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_meal_plan_recipes_plan_id
                ON meal_plan_recipes(meal_plan_id)
            """)

            await db.commit()
    
    # Recipe operations
    async def create_recipe(self, recipe_data: Dict[str, Any]) -> int:
        """Insert a new recipe and return its ID"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO recipes (
                    recipe_text, cuisine, time_minutes, effort_level,
                    dish_preference, calories_per_serving, estimated_cost,
                    used_external_ingredients, prioritize_expiring, active_profiles,
                    grocy_inventory_snapshot, user_prompt, llm_model
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recipe_data.get("recipe_text"),
                recipe_data.get("cuisine"),
                recipe_data.get("time_minutes"),
                recipe_data.get("effort_level"),
                recipe_data.get("dish_preference"),
                recipe_data.get("calories_per_serving"),
                recipe_data.get("estimated_cost"),
                recipe_data.get("used_external_ingredients"),
                recipe_data.get("prioritize_expiring"),
                json.dumps(recipe_data.get("active_profiles", [])),
                json.dumps(recipe_data.get("grocy_inventory_snapshot", {})),
                recipe_data.get("user_prompt"),
                recipe_data.get("llm_model")
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def get_recipe(self, recipe_id: int) -> Optional[Dict[str, Any]]:
        """Get a recipe by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def get_recipes(
        self, 
        limit: int = 50, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get recipes with optional filtering"""
        query = "SELECT * FROM recipes WHERE 1=1"
        params = []
        
        if filters:
            if filters.get("cuisine"):
                query += " AND cuisine = ?"
                params.append(filters["cuisine"])
            if filters.get("min_time"):
                query += " AND time_minutes >= ?"
                params.append(filters["min_time"])
            if filters.get("max_time"):
                query += " AND time_minutes <= ?"
                params.append(filters["max_time"])
            if filters.get("effort_level"):
                query += " AND effort_level = ?"
                params.append(filters["effort_level"])
            if filters.get("min_calories"):
                query += " AND calories_per_serving >= ?"
                params.append(filters["min_calories"])
            if filters.get("max_calories"):
                query += " AND calories_per_serving <= ?"
                params.append(filters["max_calories"])
            if filters.get("profile_name"):
                query += " AND active_profiles LIKE ?"
                params.append(f'%"{filters["profile_name"]}"%')
            if filters.get("search_text"):
                query += " AND recipe_text LIKE ?"
                params.append(f'%{filters["search_text"]}%')
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def delete_recipe(self, recipe_id: int) -> bool:
        """Delete a recipe by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM recipes WHERE id = ?", (recipe_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def toggle_recipe_locked(self, recipe_id: int) -> Optional[bool]:
        """Toggle lock status. Returns new is_locked value, or None if not found."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COALESCE(is_locked, 0) as is_locked FROM recipes WHERE id = ?",
                (recipe_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            new_val = 0 if row[0] else 1
            await db.execute(
                "UPDATE recipes SET is_locked = ? WHERE id = ?",
                (new_val, recipe_id)
            )
            await db.commit()
            return bool(new_val)

    async def toggle_recipe_saved(self, recipe_id: int) -> Optional[bool]:
        """Toggle saved/bookmarked status. Returns new is_saved value, or None if not found."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COALESCE(is_saved, 0) as is_saved FROM recipes WHERE id = ?",
                (recipe_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            new_val = 0 if row[0] else 1
            await db.execute(
                "UPDATE recipes SET is_saved = ? WHERE id = ?",
                (new_val, recipe_id)
            )
            await db.commit()
            return bool(new_val)

    async def create_manual_recipe(self, recipe_data: Dict[str, Any]) -> int:
        """Create a manually-entered recipe"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO recipes (
                    recipe_text, cuisine, time_minutes, effort_level,
                    calories_per_serving, is_locked, is_saved,
                    used_external_ingredients, prioritize_expiring,
                    active_profiles, llm_model
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, '[]', NULL)
            """, (
                recipe_data["recipe_text"],
                recipe_data.get("cuisine"),
                recipe_data.get("time_minutes"),
                recipe_data.get("effort_level"),
                recipe_data.get("calories_per_serving"),
                1 if recipe_data.get("is_locked") else 0,
                1 if recipe_data.get("is_saved") else 0,
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def cleanup_old_recipes(self, max_count: int):
        """Keep only the most recent N recipes, preserving locked and saved recipes"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM recipes WHERE id NOT IN (
                    SELECT id FROM recipes
                    ORDER BY created_at DESC
                    LIMIT ?
                )
                AND COALESCE(is_locked, 0) = 0
                AND COALESCE(is_saved, 0) = 0
            """, (max_count,))
            await db.commit()
    
    # Dietary profile operations
    async def create_profile(self, name: str, dietary_restrictions: str) -> int:
        """Create a new dietary profile"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO dietary_profiles (name, dietary_restrictions)
                VALUES (?, ?)
            """, (name, dietary_restrictions))
            await db.commit()
            return cursor.lastrowid
    
    async def get_profile(self, profile_id: int) -> Optional[Dict[str, Any]]:
        """Get a profile by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM dietary_profiles WHERE id = ?", (profile_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def get_all_profiles(self) -> List[Dict[str, Any]]:
        """Get all dietary profiles"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM dietary_profiles ORDER BY name"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def update_profile(
        self, 
        profile_id: int, 
        name: Optional[str] = None,
        dietary_restrictions: Optional[str] = None
    ) -> bool:
        """Update a dietary profile"""
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if dietary_restrictions is not None:
            updates.append("dietary_restrictions = ?")
            params.append(dietary_restrictions)
        
        if not updates:
            return False
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(profile_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"UPDATE dietary_profiles SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def delete_profile(self, profile_id: int) -> bool:
        """Delete a dietary profile"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM dietary_profiles WHERE id = ?", (profile_id,)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    # User preferences operations
    async def get_user_preferences(self) -> Dict[str, Any]:
        """Get the user preference document"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT content, updated_at FROM user_preferences WHERE id = 1"
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {"content": "", "updated_at": None}

    async def set_user_preferences(self, content: str) -> Dict[str, Any]:
        """Set the user preference document"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_preferences (id, content, updated_at)
                VALUES (1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    content = excluded.content,
                    updated_at = CURRENT_TIMESTAMP
            """, (content,))
            await db.commit()
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT content, updated_at FROM user_preferences WHERE id = 1"
            )
            row = await cursor.fetchone()
            return dict(row)

    # Settings operations
    async def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None
    
    async def set_setting(self, key: str, value: str):
        """Set a setting value"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            await db.commit()
    
    async def get_all_settings(self) -> Dict[str, str]:
        """Get all settings"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM settings")
            rows = await cursor.fetchall()
            return {row["key"]: row["value"] for row in rows}

    # Meal plan operations
    async def create_meal_plan(
        self,
        overview: str,
        recipes: List[Dict[str, Any]],
        request_params: Dict[str, Any],
        llm_model: str
    ) -> int:
        """Create a new meal plan with its recipes"""
        async with aiosqlite.connect(self.db_path) as db:
            # Insert the meal plan
            cursor = await db.execute("""
                INSERT INTO meal_plans (
                    overview, total_days, total_people, budget_level,
                    daily_calorie_target, active_profiles, request_params, llm_model
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                overview,
                request_params.get("days", 7),
                request_params.get("people", 2),
                request_params.get("budget_level", "moderate"),
                request_params.get("daily_calorie_target"),
                json.dumps(request_params.get("active_profiles", [])),
                json.dumps(request_params),
                llm_model
            ))
            meal_plan_id = cursor.lastrowid

            # Insert each recipe
            for recipe in recipes:
                await db.execute("""
                    INSERT INTO meal_plan_recipes (
                        meal_plan_id, day, meal_type, title, recipe_text,
                        calories_estimate, prep_time_minutes, servings, estimated_cost
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    meal_plan_id,
                    recipe.get("day", 1),
                    recipe.get("meal_type", "dinner"),
                    recipe.get("title", "Untitled"),
                    recipe.get("recipe_text", ""),
                    recipe.get("calories_estimate"),
                    recipe.get("prep_time_minutes"),
                    recipe.get("servings", 2),
                    recipe.get("estimated_cost")
                ))

            await db.commit()
            return meal_plan_id

    async def get_meal_plan(self, meal_plan_id: int) -> Optional[Dict[str, Any]]:
        """Get a meal plan with all its recipes"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Get the meal plan
            cursor = await db.execute(
                "SELECT * FROM meal_plans WHERE id = ?", (meal_plan_id,)
            )
            plan_row = await cursor.fetchone()
            if not plan_row:
                return None

            plan = dict(plan_row)

            # Get all recipes for this plan
            cursor = await db.execute(
                "SELECT * FROM meal_plan_recipes WHERE meal_plan_id = ? ORDER BY day, meal_type",
                (meal_plan_id,)
            )
            recipe_rows = await cursor.fetchall()
            plan["recipes"] = [dict(row) for row in recipe_rows]

            return plan

    async def get_meal_plans(
        self,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get meal plan summaries (without full recipe text)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute("""
                SELECT mp.*,
                       COUNT(mpr.id) as meal_count,
                       SUM(mpr.estimated_cost) as estimated_total_cost
                FROM meal_plans mp
                LEFT JOIN meal_plan_recipes mpr ON mp.id = mpr.meal_plan_id
                GROUP BY mp.id
                ORDER BY mp.created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def delete_meal_plan(self, meal_plan_id: int) -> bool:
        """Delete a meal plan and all its recipes"""
        async with aiosqlite.connect(self.db_path) as db:
            # Delete recipes first (foreign key)
            await db.execute(
                "DELETE FROM meal_plan_recipes WHERE meal_plan_id = ?",
                (meal_plan_id,)
            )
            # Delete the plan
            cursor = await db.execute(
                "DELETE FROM meal_plans WHERE id = ?", (meal_plan_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_meal_plan_recipe(
        self,
        meal_plan_id: int,
        recipe_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get a specific recipe from a meal plan"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM meal_plan_recipes WHERE meal_plan_id = ? AND id = ?",
                (meal_plan_id, recipe_id)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_meal_plan_recipe(
        self,
        meal_plan_id: int,
        recipe_id: int,
        recipe_data: Dict[str, Any]
    ) -> bool:
        """Update a specific recipe in a meal plan"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE meal_plan_recipes
                SET title = ?,
                    recipe_text = ?,
                    calories_estimate = ?,
                    prep_time_minutes = ?,
                    servings = ?,
                    estimated_cost = ?
                WHERE meal_plan_id = ? AND id = ?
            """, (
                recipe_data.get("title"),
                recipe_data.get("recipe_text"),
                recipe_data.get("calories_estimate"),
                recipe_data.get("prep_time_minutes"),
                recipe_data.get("servings"),
                recipe_data.get("estimated_cost"),
                meal_plan_id,
                recipe_id
            ))
            await db.commit()
            return cursor.rowcount > 0

    async def get_meal_plan_request_params(self, meal_plan_id: int) -> Optional[Dict[str, Any]]:
        """Get the original request params for a meal plan"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT request_params FROM meal_plans WHERE id = ?",
                (meal_plan_id,)
            )
            row = await cursor.fetchone()
            if row and row["request_params"]:
                return json.loads(row["request_params"])
            return None


# Global database instance
db = Database("../data/recipes.db")

