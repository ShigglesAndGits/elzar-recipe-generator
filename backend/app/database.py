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

            # Iterative recipe editing migration
            try:
                await db.execute("ALTER TABLE recipes ADD COLUMN last_edited TIMESTAMP")
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

            # Ideas table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ideas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    notes TEXT DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    calorie_estimate TEXT,
                    status TEXT DEFAULT 'idea',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_ideas_status
                ON ideas(status)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_ideas_created_at
                ON ideas(created_at DESC)
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

            # Prep cook sessions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS prep_cook_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    num_meals INTEGER NOT NULL DEFAULT 3,
                    portions_per_meal INTEGER NOT NULL DEFAULT 4,
                    protein_anchor TEXT,
                    calorie_target INTEGER,
                    equipment TEXT DEFAULT '[]',
                    active_profiles TEXT DEFAULT '[]',
                    user_prompt TEXT,
                    overview TEXT,
                    timeline TEXT,
                    shopping_list TEXT,
                    llm_model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_prep_cook_sessions_created_at
                ON prep_cook_sessions(created_at DESC)
            """)

            # Add prep_session_id to recipes (migration)
            try:
                await db.execute("ALTER TABLE recipes ADD COLUMN prep_session_id INTEGER")
            except Exception:
                pass  # Column already exists

            # Chat sessions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT DEFAULT 'New Chat',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at
                ON chat_sessions(updated_at DESC)
            """)

            # Chat messages table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT,
                    tool_calls TEXT,
                    tool_call_id TEXT,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id
                ON chat_messages(session_id)
            """)

            # Debriefs table (post-session feedback)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS debriefs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prep_session_id INTEGER,
                    what_was_cooked TEXT,
                    what_worked TEXT,
                    what_didnt_work TEXT,
                    what_was_wasted TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (prep_session_id) REFERENCES prep_cook_sessions(id) ON DELETE SET NULL
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_debriefs_created_at
                ON debriefs(created_at DESC)
            """)

            # Recipe nutrient ratings table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS recipe_nutrient_ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipe_id INTEGER NOT NULL,
                    nutrient TEXT NOT NULL,
                    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 10),
                    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                    UNIQUE(recipe_id, nutrient)
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_nutrient_ratings_recipe_id
                ON recipe_nutrient_ratings(recipe_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_nutrient_ratings_nutrient
                ON recipe_nutrient_ratings(nutrient)
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

    # Ideas operations
    async def create_idea(self, idea_data: Dict[str, Any]) -> int:
        """Create a new idea"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO ideas (name, notes, tags, calorie_estimate, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                idea_data["name"],
                idea_data.get("notes", ""),
                json.dumps(idea_data.get("tags", [])),
                idea_data.get("calorie_estimate"),
                idea_data.get("status", "idea"),
            ))
            await db.commit()
            return cursor.lastrowid

    async def get_idea(self, idea_id: int) -> Optional[Dict[str, Any]]:
        """Get an idea by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM ideas WHERE id = ?", (idea_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_ideas(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get ideas with optional filtering"""
        query = "SELECT * FROM ideas WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if search:
            query += " AND (name LIKE ? OR notes LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if tag:
            query += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')

        query += " ORDER BY created_at DESC"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_idea(self, idea_id: int, idea_data: Dict[str, Any]) -> bool:
        """Update an idea"""
        updates = []
        params = []

        for field in ["name", "notes", "calorie_estimate", "status"]:
            if field in idea_data:
                updates.append(f"{field} = ?")
                params.append(idea_data[field])

        if "tags" in idea_data:
            updates.append("tags = ?")
            params.append(json.dumps(idea_data["tags"]))

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(idea_id)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"UPDATE ideas SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_idea(self, idea_id: int) -> bool:
        """Delete an idea"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM ideas WHERE id = ?", (idea_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    # Prep cook session operations
    async def create_prep_cook_session(
        self,
        session_data: Dict[str, Any],
        recipes: List[Dict[str, Any]]
    ) -> int:
        """Create a prep cook session and its recipes. Returns session ID."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO prep_cook_sessions (
                    num_meals, portions_per_meal, protein_anchor,
                    calorie_target, equipment, active_profiles,
                    user_prompt, overview, timeline, shopping_list, llm_model
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_data.get("num_meals", 3),
                session_data.get("portions_per_meal", 4),
                session_data.get("protein_anchor"),
                session_data.get("calorie_target"),
                json.dumps(session_data.get("equipment", [])),
                json.dumps(session_data.get("active_profiles", [])),
                session_data.get("user_prompt"),
                session_data.get("overview"),
                session_data.get("timeline"),
                session_data.get("shopping_list"),
                session_data.get("llm_model"),
            ))
            session_id = cursor.lastrowid

            # Insert each recipe linked to this session
            for recipe in recipes:
                await db.execute("""
                    INSERT INTO recipes (
                        recipe_text, cuisine, time_minutes, effort_level,
                        calories_per_serving, estimated_cost,
                        used_external_ingredients, prioritize_expiring,
                        active_profiles, llm_model, prep_session_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    recipe.get("recipe_text"),
                    recipe.get("cuisine"),
                    recipe.get("time_minutes"),
                    recipe.get("effort_level"),
                    recipe.get("calories_per_serving"),
                    recipe.get("estimated_cost"),
                    0,
                    0,
                    json.dumps(session_data.get("active_profiles", [])),
                    session_data.get("llm_model"),
                    session_id,
                ))

            await db.commit()
            return session_id

    async def get_prep_cook_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get a prep cook session with its recipes"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM prep_cook_sessions WHERE id = ?", (session_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            session = dict(row)

            # Get linked recipes
            cursor = await db.execute(
                "SELECT * FROM recipes WHERE prep_session_id = ? ORDER BY id",
                (session_id,)
            )
            recipe_rows = await cursor.fetchall()
            session["recipes"] = [dict(r) for r in recipe_rows]
            return session

    async def get_prep_cook_sessions(
        self, limit: int = 20, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get prep cook session summaries"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT pcs.*,
                       COUNT(r.id) as recipe_count,
                       SUM(r.estimated_cost) as estimated_total_cost
                FROM prep_cook_sessions pcs
                LEFT JOIN recipes r ON r.prep_session_id = pcs.id
                GROUP BY pcs.id
                ORDER BY pcs.created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def delete_prep_cook_session(self, session_id: int) -> bool:
        """Delete a prep cook session and unlink its recipes"""
        async with aiosqlite.connect(self.db_path) as db:
            # Unlink recipes (don't delete — they stay in history)
            await db.execute(
                "UPDATE recipes SET prep_session_id = NULL WHERE prep_session_id = ?",
                (session_id,)
            )
            cursor = await db.execute(
                "DELETE FROM prep_cook_sessions WHERE id = ?",
                (session_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    # Chat operations
    async def create_chat_session(self, name: str = "New Chat") -> int:
        """Create a new chat session"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO chat_sessions (name) VALUES (?)", (name,)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_chat_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get a chat session by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM chat_sessions WHERE id = ?", (session_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_chat_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent chat sessions"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM chat_sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_chat_session_name(self, session_id: int, name: str) -> bool:
        """Update a chat session name"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE chat_sessions SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (name, session_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def touch_chat_session(self, session_id: int):
        """Update the session's updated_at timestamp"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (session_id,)
            )
            await db.commit()

    async def delete_chat_session(self, session_id: int) -> bool:
        """Delete a chat session and all its messages"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM chat_messages WHERE session_id = ?", (session_id,)
            )
            cursor = await db.execute(
                "DELETE FROM chat_sessions WHERE id = ?", (session_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def add_chat_message(self, session_id: int, message: Dict[str, Any]) -> int:
        """Add a message to a chat session"""
        async with aiosqlite.connect(self.db_path) as db:
            tool_calls = message.get("tool_calls")
            if tool_calls and not isinstance(tool_calls, str):
                tool_calls = json.dumps(tool_calls)
            cursor = await db.execute("""
                INSERT INTO chat_messages (session_id, role, content, tool_calls, tool_call_id, name)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                message["role"],
                message.get("content"),
                tool_calls,
                message.get("tool_call_id"),
                message.get("name"),
            ))
            # Touch the session
            await db.execute(
                "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (session_id,)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_chat_messages(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all messages for a chat session"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id",
                (session_id,)
            )
            rows = await cursor.fetchall()
            messages = []
            for row in rows:
                msg = dict(row)
                # Parse tool_calls JSON back
                if msg.get("tool_calls") and isinstance(msg["tool_calls"], str):
                    try:
                        msg["tool_calls"] = json.loads(msg["tool_calls"])
                    except json.JSONDecodeError:
                        pass
                messages.append(msg)
            return messages

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


    # Debrief operations
    async def create_debrief(self, debrief_data: Dict[str, Any]) -> int:
        """Create a new debrief entry and return its ID."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO debriefs (prep_session_id, what_was_cooked, what_worked,
                                      what_didnt_work, what_was_wasted, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                debrief_data.get("prep_session_id"),
                debrief_data.get("what_was_cooked"),
                debrief_data.get("what_worked"),
                debrief_data.get("what_didnt_work"),
                debrief_data.get("what_was_wasted"),
                debrief_data.get("notes"),
            ))
            await db.commit()
            return cursor.lastrowid

    async def get_debriefs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent debriefs, newest first."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM debriefs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # Nutrient rating operations
    async def save_nutrient_ratings(self, recipe_id: int, ratings: Dict[str, int]) -> None:
        """Save nutrient ratings for a recipe. Upserts — safe to call multiple times."""
        async with aiosqlite.connect(self.db_path) as db:
            for nutrient, rating in ratings.items():
                await db.execute("""
                    INSERT INTO recipe_nutrient_ratings (recipe_id, nutrient, rating)
                    VALUES (?, ?, ?)
                    ON CONFLICT(recipe_id, nutrient) DO UPDATE SET rating = excluded.rating
                """, (recipe_id, nutrient, max(1, min(10, rating))))
            await db.commit()

    async def get_nutrient_ratings(self, recipe_id: int) -> Dict[str, int]:
        """Get nutrient ratings for a single recipe."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT nutrient, rating FROM recipe_nutrient_ratings WHERE recipe_id = ?",
                (recipe_id,)
            )
            rows = await cursor.fetchall()
            return {row["nutrient"]: row["rating"] for row in rows}

    async def get_nutritional_overview(self, days: int = 14, limit: int = 50) -> Dict[str, Any]:
        """
        Aggregate nutrient ratings across recent recipes.
        Returns per-nutrient averages, recipe count, and per-recipe breakdown.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Get recent recipes with ratings
            cursor = await db.execute("""
                SELECT r.id, r.recipe_text, r.cuisine, r.created_at,
                       rnr.nutrient, rnr.rating
                FROM recipes r
                JOIN recipe_nutrient_ratings rnr ON r.id = rnr.recipe_id
                WHERE r.created_at >= datetime('now', ? || ' days')
                ORDER BY r.created_at DESC
            """, (f"-{days}",))
            rows = await cursor.fetchall()

            if not rows:
                return {"recipes_analyzed": 0, "averages": {}, "gaps": [], "recipes": []}

            # Aggregate
            from collections import defaultdict
            nutrient_sums = defaultdict(list)
            recipes_seen = {}
            for row in rows:
                rid = row["id"]
                if rid not in recipes_seen:
                    recipes_seen[rid] = {
                        "id": rid,
                        "cuisine": row["cuisine"],
                        "created_at": row["created_at"],
                        "ratings": {},
                    }
                recipes_seen[rid]["ratings"][row["nutrient"]] = row["rating"]
                nutrient_sums[row["nutrient"]].append(row["rating"])

            averages = {
                nutrient: round(sum(vals) / len(vals), 1)
                for nutrient, vals in nutrient_sums.items()
            }
            # Gaps: nutrients averaging below 4
            gaps = [n for n, avg in averages.items() if avg < 4.0]

            return {
                "recipes_analyzed": len(recipes_seen),
                "days": days,
                "averages": averages,
                "gaps": gaps,
                "recipes": list(recipes_seen.values()),
            }


# Global database instance
db = Database("../data/recipes.db")

