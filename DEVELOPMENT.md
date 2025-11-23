# Elzar Development Notes

## Architecture Overview

Elzar follows a modern client-server architecture:

```
┌─────────────────────┐
│   React Frontend    │  Port 5173 (Vite dev server)
│   (Vite + Tailwind) │
└──────────┬──────────┘
           │ HTTP/REST
           ▼
┌─────────────────────┐
│   FastAPI Backend   │  Port 8000
│   (Python + SQLite) │
└──────────┬──────────┘
           │
    ┌──────┴─────────┬──────────────┐
    ▼                ▼              ▼
┌─────────┐    ┌──────────┐   ┌─────────┐
│  Grocy  │    │   LLM    │   │ Apprise │
│   API   │    │   API    │   │  (opt)  │
└─────────┘    └──────────┘   └─────────┘
```

## Key Design Decisions

### 1. Why SQLite?
- **Simple**: Single file database, easy to backup
- **Sufficient**: Handles 1000s of recipes easily
- **Portable**: Works everywhere Python works
- **No setup**: No database server to configure
- **Upgrade path**: Can migrate to PostgreSQL later if needed

### 2. Why FastAPI?
- **Async**: Perfect for LLM API calls (10-30 second waits)
- **Type hints**: Pydantic models for validation
- **Auto docs**: Swagger UI and ReDoc out of the box
- **Modern**: Python 3.8+ with async/await
- **Fast**: One of the fastest Python frameworks

### 3. Why React?
- **Component reuse**: Generator controls used across pages
- **State management**: Easy to manage complex form state
- **Ecosystem**: Great libraries (react-markdown, etc.)
- **Developer experience**: Hot module reloading with Vite

### 4. OpenAI-Compatible API
- **Flexibility**: Works with OpenRouter, OpenAI, Anthropic, local Ollama
- **Future-proof**: User can switch providers easily
- **Cost control**: Use free tier models or local inference

## Code Organization

### Backend Structure

```
backend/app/
├── main.py              # FastAPI app, CORS, startup/shutdown
├── config.py            # Pydantic settings from environment
├── models.py            # Request/response models
├── database.py          # SQLite operations
├── routers/             # API endpoints by feature
│   ├── recipes.py       # Generation, regenerate, download
│   ├── history.py       # Browse, filter, delete
│   ├── profiles.py      # CRUD for dietary profiles
│   └── settings.py      # Config and connection tests
├── services/            # External API clients
│   ├── grocy_client.py  # Grocy API wrapper
│   ├── llm_client.py    # OpenAI-compatible LLM client
│   └── notification.py  # Apprise notifications
└── utils/               # Helpers
    └── recipe_parser.py # Extract metadata from LLM output
```

### Frontend Structure

```
frontend/src/
├── main.jsx             # React entry point
├── App.jsx              # Router and navigation
├── api.js               # Axios API client
├── index.css            # Tailwind + custom styles
└── pages/               # Page components
    ├── Generator.jsx    # Main recipe generation UI
    ├── History.jsx      # Browse and filter recipes
    ├── Profiles.jsx     # Manage dietary profiles
    └── Settings.jsx     # Config and testing
```

## Data Flow

### Recipe Generation Flow

1. **User interaction**: User configures options and presses BAM!
2. **Frontend**: `Generator.jsx` collects form state
3. **API call**: POST to `/api/recipes/generate` with parameters
4. **Backend - Grocy**: Fetch inventory from Grocy API
5. **Backend - Profiles**: Load active dietary profiles from DB
6. **Backend - LLM**: Build prompt and call LLM API
7. **Backend - Parse**: Extract metadata from LLM response
8. **Backend - Store**: Save to SQLite with metadata
9. **Backend - Cleanup**: Delete old recipes if > MAX_RECIPE_HISTORY
10. **Response**: Return recipe to frontend
11. **Frontend**: Display recipe with React Markdown

### Recipe History Flow

1. **User interaction**: User opens History page
2. **Frontend**: `History.jsx` mounts, useEffect triggers
3. **API call**: GET `/api/history/` with filter params
4. **Backend**: Query SQLite with filters
5. **Response**: Return array of recipes
6. **Frontend**: Display in list, user selects one
7. **Frontend**: Show full recipe in detail pane

## LLM Prompt Engineering

The prompt is carefully structured to get consistent results:

```
You are Elzar, an expert chef AI assistant! BAM! 🌶️

Generate a delicious recipe based on the following information:

AVAILABLE INGREDIENTS:
- [Ingredient list from Grocy]

CONSTRAINTS:
- Cuisine: [selected]
- Maximum cooking time: [X] minutes
- Effort level: [Low/Medium/High]
- [etc...]

DIETARY RESTRICTIONS:
- [Person]: [Their restrictions]

[Instructions for format]

At the end, include metadata in this exact format:
---
METADATA:
Cuisine: [type]
Total Time: [minutes]
Effort: [level]
Calories: [number]
---
```

### Why This Structure Works

1. **Clear role**: "You are Elzar" sets the tone
2. **Structured data**: Ingredients in list format
3. **Explicit constraints**: Leave no ambiguity
4. **Dietary first**: Critical information upfront
5. **Format guidance**: Ensures parseable output
6. **Metadata section**: Easy regex extraction

## Database Schema Details

### Recipes Table

```sql
recipes (
    id                    INTEGER PRIMARY KEY,
    created_at            TIMESTAMP,
    recipe_text           TEXT,           -- Full markdown from LLM
    cuisine               TEXT,           -- Extracted or user-selected
    time_minutes          INTEGER,        -- Extracted from metadata
    effort_level          TEXT,           -- Low/Medium/High
    dish_preference       TEXT,           -- User's dish cleanup pref
    calories_per_serving  INTEGER,        -- Extracted from metadata
    used_external_ingredients BOOLEAN,    -- Whether external allowed
    prioritize_expiring   BOOLEAN,        -- Whether expiring prioritized
    active_profiles       TEXT,           -- JSON array of names
    grocy_inventory_snapshot TEXT,        -- JSON of inventory at time
    user_prompt           TEXT,           -- Additional user notes
    llm_model             TEXT            -- Model used for generation
)
```

**Design notes:**
- `active_profiles` as JSON: Flexible, no join table needed
- `grocy_inventory_snapshot`: Audit trail, can regenerate
- Indexes on commonly filtered columns (cuisine, time, calories)

### Dietary Profiles Table

```sql
dietary_profiles (
    id                   INTEGER PRIMARY KEY,
    name                 TEXT UNIQUE,     -- "John", "Sarah"
    dietary_restrictions TEXT,            -- Free-form description
    created_at           TIMESTAMP,
    updated_at           TIMESTAMP
)
```

**Design notes:**
- Simple key-value structure
- Text restrictions (not structured) for flexibility
- Unique name constraint prevents duplicates

## API Patterns

### Error Handling

All endpoints follow this pattern:

```python
try:
    # Operation
    result = await some_operation()
    return result
except SpecificError as e:
    raise HTTPException(
        status_code=status.HTTP_XXX_ERROR,
        detail="User-friendly message"
    )
```

### Response Models

Pydantic models ensure type safety:

```python
class RecipeResponse(BaseModel):
    id: int
    recipe_text: str
    cuisine: Optional[str]
    # ... fields match database schema
    created_at: datetime
```

Benefits:
- Automatic validation
- Auto-generated API docs
- Type hints for IDE

## Frontend Patterns

### State Management

Local state for forms, no global state library needed:

```javascript
const [cuisine, setCuisine] = useState('No Preference');
const [timeMinutes, setTimeMinutes] = useState(60);
// ... more state
```

### API Calls

Axios with async/await:

```javascript
const handleGenerate = async () => {
  setLoading(true);
  try {
    const recipe = await generateRecipe(params);
    setCurrentRecipe(recipe);
  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
};
```

### Styling Strategy

Tailwind utility classes for rapid development:

```jsx
<button className="bg-elzar-red hover:bg-red-600 text-white px-4 py-2 rounded-lg">
  BAM!
</button>
```

Custom classes for complex styling (recipes, kiosk mode).

## Performance Considerations

### Backend

1. **Async operations**: LLM calls don't block
2. **Database indexes**: Fast filtering on history
3. **Connection pooling**: httpx reuses connections
4. **Recipe cleanup**: Automatic old recipe deletion

### Frontend

1. **Lazy loading**: Pages loaded on demand
2. **Pagination**: History limited to 50 per page
3. **Debouncing**: Could add for search filters
4. **Markdown rendering**: react-markdown is lightweight

## Security Considerations

### Current Implementation

1. **API keys in backend**: Never exposed to frontend
2. **CORS**: Configured for localhost (tighten in production)
3. **Input validation**: Pydantic models validate all inputs
4. **SQL injection**: SQLite parameterized queries

### For Production

1. **HTTPS**: Use reverse proxy (nginx)
2. **Authentication**: Add if exposing externally
3. **Rate limiting**: Prevent LLM API abuse
4. **CORS**: Restrict to specific domains
5. **Secrets**: Use Docker secrets or HashiCorp Vault

## Future Enhancements

### Planned Features (Phase 10+)

1. **Save to Grocy**: POST recipes to Grocy recipes endpoint
2. **Shopping list**: Add missing ingredients via Grocy API
3. **Consume ingredients**: Mark items as consumed
4. **Favorites**: Star recipes, separate table
5. **Tags**: User-defined tags for categorization

### Technical Debt

1. **Tests**: Add pytest for backend, Jest for frontend
2. **Error boundaries**: React error boundaries for better UX
3. **Logging**: Structured logging with levels
4. **Monitoring**: Health checks, metrics
5. **Caching**: Cache Grocy inventory for short period

## Development Workflow

### Backend Development

```bash
cd backend
source venv/bin/activate
python -m app.main
# Edit code, FastAPI auto-reloads
```

### Frontend Development

```bash
cd frontend
npm run dev
# Edit code, Vite hot-reloads
```

### Testing Locally

1. Use Settings page to test connections
2. Check backend logs in terminal
3. Use browser DevTools for frontend debugging
4. API docs at http://localhost:8000/docs

## Deployment Notes

### Docker (Future)

Multi-stage build:
1. Build frontend (npm build)
2. Serve frontend static files with FastAPI
3. Single container, easy deployment

### Environment Variables

All config via `.env`:
- No hardcoded values
- Easy to change per environment
- Docker-friendly

### Data Persistence

Mount `/data` volume:
- SQLite database
- Exported recipe text files

## Contributing Guidelines

If extending Elzar:

1. **Backend**: Add new routers for new features
2. **Frontend**: Create new pages/components
3. **Database**: Add migrations (currently manual)
4. **API**: Update Pydantic models for new endpoints
5. **Docs**: Update README and this file

## Useful Commands

```bash
# Backend
pip freeze > requirements.txt  # Update deps
python -m pytest                # Run tests (when added)

# Frontend
npm run build                   # Production build
npm run preview                 # Preview production build

# Database
sqlite3 data/recipes.db ".schema"  # View schema
sqlite3 data/recipes.db ".tables"  # List tables

# Git
git log --oneline --graph      # View history
```

---

BAM! Happy hacking! 🌶️

