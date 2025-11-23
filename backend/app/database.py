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
                    used_external_ingredients BOOLEAN,
                    prioritize_expiring BOOLEAN,
                    active_profiles TEXT,
                    grocy_inventory_snapshot TEXT,
                    user_prompt TEXT,
                    llm_model TEXT
                )
            """)
            
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
            
            await db.commit()
    
    # Recipe operations
    async def create_recipe(self, recipe_data: Dict[str, Any]) -> int:
        """Insert a new recipe and return its ID"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO recipes (
                    recipe_text, cuisine, time_minutes, effort_level,
                    dish_preference, calories_per_serving, used_external_ingredients,
                    prioritize_expiring, active_profiles, grocy_inventory_snapshot,
                    user_prompt, llm_model
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recipe_data.get("recipe_text"),
                recipe_data.get("cuisine"),
                recipe_data.get("time_minutes"),
                recipe_data.get("effort_level"),
                recipe_data.get("dish_preference"),
                recipe_data.get("calories_per_serving"),
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
    
    async def cleanup_old_recipes(self, max_count: int):
        """Keep only the most recent N recipes"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM recipes WHERE id NOT IN (
                    SELECT id FROM recipes 
                    ORDER BY created_at DESC 
                    LIMIT ?
                )
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


# Global database instance
db = Database("../data/recipes.db")

