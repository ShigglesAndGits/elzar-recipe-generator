# Elzar Backend 🌶️

BAM! This is the FastAPI backend for Elzar, the Grocy Recipe Generator.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

4. Run the server:
```bash
cd backend
python -m app.main
```

Or with uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints

### Recipes
- `POST /api/recipes/generate` - Generate a new recipe (BAM!)
- `POST /api/recipes/regenerate/{id}` - Regenerate with same parameters
- `GET /api/recipes/{id}` - Get a specific recipe
- `GET /api/recipes/{id}/download` - Download recipe as text file
- `POST /api/recipes/{id}/send` - Send recipe to phone

### History
- `GET /api/history/` - Get recipe history with filters
- `DELETE /api/history/{id}` - Delete a recipe
- `GET /api/history/count` - Get total recipe count

### Profiles
- `POST /api/profiles/` - Create dietary profile
- `GET /api/profiles/` - Get all profiles
- `GET /api/profiles/{id}` - Get specific profile
- `PUT /api/profiles/{id}` - Update profile
- `DELETE /api/profiles/{id}` - Delete profile

### Settings
- `GET /api/settings/config` - Get app configuration
- `GET /api/settings/` - Get all settings
- `GET /api/settings/{key}` - Get specific setting
- `PUT /api/settings/{key}` - Set a setting value
- `GET /api/settings/test/grocy` - Test Grocy connection
- `GET /api/settings/test/llm` - Test LLM connection

## Configuration

Environment variables (see `.env.example`):

- `GROCY_URL` - Your Grocy instance URL
- `GROCY_API_KEY` - Grocy API key
- `LLM_API_URL` - OpenAI-compatible API URL
- `LLM_API_KEY` - API key for LLM
- `LLM_MODEL` - Model name to use
- `MAX_RECIPE_HISTORY` - Maximum recipes to keep (default: 1000)
- `DATABASE_PATH` - Path to SQLite database
- `RECIPE_EXPORT_PATH` - Path for recipe text file exports
- `APPRISE_URL` - Apprise notification URL (optional)

## Development

The backend uses:
- **FastAPI** - Modern async web framework
- **SQLite** - Lightweight database
- **httpx** - Async HTTP client for API calls
- **Pydantic** - Data validation
- **Apprise** - Notification service

BAM! Happy cooking! 🌶️

