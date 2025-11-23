# Elzar - Grocy Recipe Generator 🌶️

*BAM! Let's make cooking delicious!*

A smart recipe generator that creates meals based on your Grocy inventory, powered by AI.

## Project Overview

Elzar is a self-hosted web application that:
- Pulls inventory from Grocy's API
- Uses LLM AI to generate creative recipes based on what you have
- Displays recipes with rich controls for cuisine, time, effort, and dietary needs
- Manages household dietary restriction profiles
- Provides a kiosk mode for a fridge-mounted Raspberry Pi touchscreen
- Offers mobile-friendly recipe history browsing
- Sends recipes to your phone via notifications

## Tech Stack

- **Backend:** FastAPI (Python)
- **Frontend:** React with Vite + Tailwind CSS
- **Database:** SQLite
- **LLM:** OpenAI-compatible API (OpenRouter/Gemini/Local)
- **Notifications:** Apprise (multi-service support)

## Project Structure

```
grocy-recipe-generator-custom/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Configuration management
│   │   ├── models.py            # Pydantic models
│   │   ├── database.py          # SQLite setup & operations
│   │   ├── routers/
│   │   │   ├── recipes.py       # Recipe generation endpoints
│   │   │   ├── history.py       # Recipe history endpoints
│   │   │   ├── profiles.py      # Dietary profile management
│   │   │   └── settings.py      # Settings management
│   │   ├── services/
│   │   │   ├── grocy_client.py  # Grocy API wrapper
│   │   │   ├── llm_client.py    # OpenAI-compatible LLM client
│   │   │   └── notification.py  # Apprise notification service
│   │   └── utils/
│   │       └── recipe_parser.py # Extract metadata from recipes
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── pages/
│   │   │   ├── Generator.jsx    # Main recipe generation page (BAM!)
│   │   │   ├── History.jsx      # Recipe history browser
│   │   │   ├── Profiles.jsx     # Manage dietary profiles
│   │   │   └── Settings.jsx     # Configuration page
│   │   ├── components/
│   │   │   ├── RecipeDisplay.jsx
│   │   │   ├── ControlPanel.jsx # All the toggles/sliders
│   │   │   ├── ProfileToggles.jsx # Household member toggles
│   │   │   └── LoadingState.jsx
│   │   └── styles/
│   │       └── kiosk.css        # Kiosk-specific styles
│   ├── package.json
│   └── vite.config.js
├── data/                        # Created at runtime
│   ├── recipes.db              # SQLite database
│   └── recipes/                # Downloaded recipe text files
├── Dockerfile                   # (Phase 9)
├── docker-compose.yml           # (Phase 9)
├── PROJECT_PLAN.md             # This file
└── README.md
```

## Development Phases

### Phase 1: Core Backend (MVP)
- [ ] FastAPI setup with basic structure
- [ ] SQLite database with recipe history table
- [ ] Configuration management (env vars for Grocy URL, API keys, etc.)
- [ ] Grocy API client (fetch inventory with expiration dates)
- [ ] OpenAI-compatible LLM client
- [ ] Recipe generation endpoint with all parameters
- [ ] Recipe history CRUD endpoints

### Phase 2: Dietary Profiles System
- [ ] Database table for household profiles
- [ ] Profile CRUD endpoints (create, read, update, delete)
- [ ] Profile model with name and dietary restrictions text
- [ ] API endpoint to get all profiles for toggles

### Phase 3: Frontend MVP
- [ ] React + Vite setup with Tailwind
- [ ] Recipe generator page with all controls:
  - Cuisine dropdown (Mexican, Asian, Thai, Japanese, Chinese, Italian, Indian, No Preference)
  - Household member toggles (dietary restrictions)
  - Expiring ingredients toggle
  - Time slider (15 min - 3 hours)
  - Effort slider (Low/Medium/High)
  - Dishes radio buttons (No dishes/Few dishes/I don't care)
  - Calorie target input
  - "Use ingredients not in fridge" toggle
- [ ] Recipe display component
- [ ] **BAM!** button (generate)
- [ ] Regenerate button (with same parameters)
- [ ] Clear button
- [ ] Download as text file button
- [ ] Loading/streaming state

### Phase 4: Recipe History
- [ ] History page with list view
- [ ] Filter by:
  - Cuisine
  - Time range (min/max)
  - Effort level
  - Calories
  - Date range
  - Dietary profiles used
- [ ] Search functionality (full text)
- [ ] Click to view full recipe
- [ ] Pagination (50 per page)
- [ ] Delete individual recipes
- [ ] Download from history

### Phase 5: Profile Management UI
- [ ] Profiles management page
- [ ] Add new household member
- [ ] Edit dietary restrictions
- [ ] Delete profiles
- [ ] Simple form: Name + Dietary Restrictions (textarea)

### Phase 6: Kiosk Mode
- [ ] Kiosk mode toggle in settings
- [ ] Full-screen layout optimized for 800x480 (Raspberry Pi 7" touchscreen)
- [ ] Large touch-friendly buttons (min 60px)
- [ ] Simplified UI (hide advanced history features in kiosk mode)
- [ ] Auto-hide/minimal nav bar
- [ ] Consider screensaver/idle timeout (optional)
- [ ] High contrast, readable fonts

### Phase 7: Mobile Optimization
- [ ] Responsive design for mobile
- [ ] Touch-friendly controls
- [ ] PWA manifest (optional: install as app)
- [ ] Mobile-optimized history browser
- [ ] Swipe gestures (optional)

### Phase 8: Notifications
- [ ] Settings page for notification configuration
- [ ] Apprise integration
- [ ] "Send to Phone" button on generated recipes
- [ ] Send recipe as formatted text
- [ ] Support multiple notification services

### Phase 9: Settings & Configuration UI
- [ ] Settings page UI
- [ ] Grocy URL configuration
- [ ] Grocy API key
- [ ] LLM API endpoint configuration
- [ ] LLM API key
- [ ] LLM model name
- [ ] Max recipe history count
- [ ] Notification service setup (Apprise URL)
- [ ] Kiosk mode toggle
- [ ] Theme preferences (optional)

### Phase 10: Future Features
- [ ] Save recipe to Grocy (as recipe entity)
- [ ] Add missing ingredients to Grocy shopping list
- [ ] Mark recipe ingredients as consumed in Grocy
- [ ] Recipe favorites/rating system
- [ ] Recipe tags (user-defined)
- [ ] Export all recipes as JSON/CSV
- [ ] Recipe notes/modifications

### Phase 11: Docker & Deployment
- [ ] Create Dockerfile (multi-stage build)
- [ ] docker-compose.yml with volume mounts
- [ ] Environment variable documentation
- [ ] Health checks
- [ ] README with setup instructions
- [ ] Volume for data persistence
- [ ] Port configuration

## Database Schema (SQLite)

```sql
-- recipes table
CREATE TABLE recipes (
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
    active_profiles TEXT,  -- JSON array of profile names used
    grocy_inventory_snapshot TEXT,  -- JSON snapshot of what was available
    user_prompt TEXT,
    llm_model TEXT
);

-- settings table
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- dietary_profiles table
CREATE TABLE dietary_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    dietary_restrictions TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_recipes_created_at ON recipes(created_at DESC);
CREATE INDEX idx_recipes_cuisine ON recipes(cuisine);
CREATE INDEX idx_recipes_time ON recipes(time_minutes);
CREATE INDEX idx_recipes_calories ON recipes(calories_per_serving);
CREATE INDEX idx_profiles_name ON dietary_profiles(name);
```

## Configuration (.env example)

```bash
# Grocy Configuration
GROCY_URL=https://groceries.bironfamily.net
GROCY_API_KEY=your_api_key_here

# LLM Configuration
LLM_API_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your_openrouter_key
LLM_MODEL=google/gemini-2.0-flash-exp:free

# Application Settings
MAX_RECIPE_HISTORY=1000
DATABASE_PATH=./data/recipes.db
RECIPE_EXPORT_PATH=./data/recipes

# Notification (Optional)
APPRISE_URL=  # e.g., pbul://your_pushbullet_key

# Server
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_PORT=5173  # Vite dev server
```

## Recipe Generation Controls

### Cuisine Options
- Mexican
- Asian (General)
- Thai
- Japanese
- Chinese
- Italian
- Indian
- Mediterranean
- American
- French
- No Preference (default)

### Household Member Toggles
- Dynamically populated from dietary_profiles table
- Each toggle shows member name
- When enabled, their dietary restrictions are added to LLM prompt
- Example: "John: Gluten-free, lactose intolerant"

### Other Controls
- **Prioritize Expiring:** Toggle (uses Grocy expiration dates)
- **Time Range:** Slider (15 min - 180 min)
- **Effort Level:** Slider (Low / Medium / High)
- **Dish Preference:** Radio buttons (No dishes / Few dishes / I don't care)
- **Target Calories:** Number input (per serving)
- **Use Ingredients Not in Fridge:** Toggle (allow external ingredients)

## LLM Prompt Strategy

**Prompt Structure:**
```
You are Elzar, an expert chef AI. Generate a recipe based on the following:

AVAILABLE INGREDIENTS:
[JSON list from Grocy with quantities and expiration dates]

CONSTRAINTS:
- Cuisine: [selected cuisine or "any"]
- Time: Maximum [X] minutes
- Effort: [Low/Medium/High]
- Dish cleanup: [preference]
- Calories: Target [X] per serving
- Use only fridge ingredients: [Yes/No]

DIETARY RESTRICTIONS:
[For each toggled household member]
- [Name]: [Their restrictions]

ADDITIONAL NOTES:
- [If prioritize expiring is on] Please prioritize ingredients expiring soon: [list items]

Please generate a detailed recipe in markdown format including:
- Recipe title
- Prep time and cook time
- Servings
- Ingredients list with quantities
- Step-by-step instructions
- Estimated calories per serving
- Any relevant tips

Also provide metadata in this format at the end:
---
METADATA:
Cuisine: [detected cuisine]
Total Time: [minutes]
Effort: [Low/Medium/High]
Calories: [per serving]
---
```

## Recipe Text File Format

When downloaded, recipes should be saved as:
```
recipe_[timestamp].txt
```

Example content:
```
Recipe Generated: 2025-11-23 14:30:22
Cuisine: Thai
Time: 45 minutes
Effort: Medium
Calories: 520 per serving
Household Members: John, Sarah

========================================

[Full recipe markdown content from LLM]

========================================

Generated by Elzar 🌶️
BAM! https://github.com/your-repo
```

## UI/UX Guidelines

### Kiosk Mode (800x480 Resolution)
- **Large buttons:** Minimum 60x60px touch targets
- **High contrast:** Dark mode with vibrant accent colors
- **Minimal text:** Icons + short labels
- **No hover states:** Everything touch-based
- **Simplified navigation:** Home (Generator) and History only
- **Auto-hide chrome:** Minimal header/footer
- **Loading states:** Large, clear progress indicators

### Mobile Mode
- **Responsive breakpoints:** Standard mobile sizes
- **Bottom navigation:** Thumb-friendly
- **Swipeable controls:** Consider gesture support
- **Compact history:** Card-based layout
- **Pull-to-refresh:** For history page

### Desktop Mode
- **Sidebar navigation:** Generator, History, Profiles, Settings
- **Multi-column layout:** Controls on left, recipe on right
- **Keyboard shortcuts:** Optional power-user features

## Suggested Development Order

1. ✅ **Project planning & structure** 
2. **Backend skeleton** - FastAPI running with test endpoint
3. **Database setup** - SQLite with all tables
4. **Grocy client** - Test pulling inventory
5. **LLM client** - Test generating a simple recipe
6. **Generation endpoint** - Combine Grocy + LLM with all parameters
7. **Profile endpoints** - CRUD for dietary profiles
8. **Frontend setup** - React + Vite + Tailwind
9. **Generator page** - All controls + BAM! button
10. **Recipe display** - Show generated recipes nicely
11. **History storage** - Save to database
12. **History page** - Browse and filter
13. **Profile management page** - Add/edit household members
14. **Settings page** - Configure everything
15. **Kiosk styling** - Test on 800x480
16. **Mobile styling** - Responsive design
17. **Notifications** - Send to phone
18. **Text file downloads** - Save recipes offline
19. **Polish & testing** - Fix bugs, improve UX
20. **Dockerize** - Final deployment setup

## Key Features Summary

### Core Features (MVP)
- ✅ Recipe generation with LLM
- ✅ Grocy inventory integration
- ✅ **BAM!** button to generate
- ✅ Regenerate with same parameters
- ✅ Clear current recipe
- ✅ Recipe history (last 1000, configurable)
- ✅ Dietary profile toggles
- ✅ Full control panel (cuisine, time, effort, etc.)
- ✅ Download recipe as text file

### Enhanced Features
- ✅ Kiosk mode for Raspberry Pi touchscreen
- ✅ Mobile-friendly responsive design
- ✅ Recipe filtering in history
- ✅ Notification service (send to phone)
- ✅ Profile management UI

### Future Features
- Save recipe to Grocy
- Add missing ingredients to shopping list
- Mark ingredients as consumed
- Recipe favorites/ratings
- Recipe tags
- Export history

## Notes & Considerations

- **Grocy API quirks:** Some endpoints can be tricky; plan to iterate
- **LLM response time:** 10-30 seconds typical; need good loading state
- **Raspberry Pi:** Can't run local LLM; must call external API
- **Text files vs DB:** Store full text in both for offline access
- **Concurrent requests:** FastAPI handles async well for LLM calls
- **Error handling:** Grocy down? LLM API error? Plan for graceful failures

## Success Criteria

The project is "done" when:
1. You can press **BAM!** and get a recipe based on Grocy inventory
2. Dietary profiles work and restrict recipes appropriately
3. Recipe history is browsable and filterable
4. It looks great on a 7" touchscreen (800x480)
5. It works well on mobile phones
6. You can send recipes to your phone
7. Everything runs in a single Docker container
8. Configuration is easy via environment variables

---

*Let's kick it up a notch! BAM! 🌶️*

