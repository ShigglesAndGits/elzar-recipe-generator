# Elzar - Grocy Recipe Generator 🌶️

*BAM! Let's make cooking delicious!*

A smart recipe generator that creates meals based on your Grocy inventory, powered by AI.

## Project Overview

Elzar is a self-hosted web application that:
- Pulls inventory from Grocy's API
- Uses LLM AI to generate creative recipes based on what you have
- Displays recipes with rich controls for cuisine, time, effort, and dietary needs
- Manages household dietary restriction profiles
- Provides bulk inventory management (receipts, ingredient lists)
- Integrates deeply with Grocy (consume, shopping list, save recipes)
- Offers recipe history browsing
- Sends recipes to your phone via notifications (planned)

## Tech Stack

- **Backend:** FastAPI (Python 3.9+)
- **Frontend:** React 18 with Vite + Tailwind CSS
- **Database:** SQLite
- **LLM:** OpenAI-compatible API (OpenRouter/Gemini/Ollama)
- **Notifications:** Apprise (multi-service support)
- **Deployment:** Systemd services, Docker-ready

## Current Version: 1.1.0

### Version History

**v1.1.0** (Current)
- Bulk inventory management (parse receipts/lists)
- Recipe integration (consume, shopping list, save)
- Ingredient review workflow with manual editing
- Auto-creation of missing products and units
- One-click setup for units, conversions, and locations
- Stock checking before consume operations
- Smart shopping list (only adds missing items)
- LLM-powered inventory matching

**v1.0.0**
- Core recipe generation
- Grocy inventory integration
- Dietary profile management
- UI-based configuration
- Recipe history
- Elzar personality toggle
- Serving size options
- High leftover potential

## Project Structure

```
elzar-recipe-generator/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app entry point (v1.1.0)
│   │   ├── config.py                  # Configuration from env vars
│   │   ├── models.py                  # Pydantic models (updated v1.1)
│   │   ├── database.py                # SQLite setup & operations
│   │   ├── routers/
│   │   │   ├── recipes.py             # Recipe generation & integration (v1.1)
│   │   │   ├── inventory.py           # Inventory management (NEW v1.1)
│   │   │   ├── history.py             # Recipe history endpoints
│   │   │   ├── profiles.py            # Dietary profile management
│   │   │   └── settings.py            # Settings, testing, setup (v1.1)
│   │   ├── services/
│   │   │   ├── grocy_client.py        # Grocy API wrapper (expanded v1.1)
│   │   │   ├── llm_client.py          # OpenAI-compatible LLM client
│   │   │   ├── inventory_matcher.py   # AI inventory parsing (NEW v1.1)
│   │   │   └── notification.py        # Apprise notification service
│   │   └── utils/
│   │       └── config_manager.py      # Hybrid config management
│   ├── requirements.txt
│   └── .env                           # Environment variables
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Generator.jsx          # Main recipe generation page (v1.1)
│   │   │   ├── InventoryManager.jsx   # Bulk inventory management (NEW v1.1)
│   │   │   ├── History.jsx            # Recipe history browser
│   │   │   ├── Profiles.jsx           # Dietary profile management
│   │   │   └── Settings.jsx           # Settings & configuration (v1.1)
│   │   ├── components/
│   │   │   ├── RecipeIngredientReview.jsx  # Ingredient review modal (NEW v1.1)
│   │   │   └── GrocyActionModal.jsx        # Action result display (NEW v1.1)
│   │   ├── api.js                     # Backend API client (expanded v1.1)
│   │   └── App.jsx                    # Main app & routing
│   ├── package.json
│   └── vite.config.js
├── data/
│   └── recipes.db                     # SQLite database
├── setup.sh                           # Automated setup script
├── elzar-backend.service              # Systemd service (backend)
├── elzar-frontend.service             # Systemd service (frontend)
├── PROJECT_PLAN.md                    # This file
├── PROJECT_PLAN_V1.1.md               # v1.1 feature plan
├── DEVELOPMENT.md                     # Development notes
└── README.md                          # User documentation
```

## Database Schema

### Tables

**recipes**
- `id` (INTEGER PRIMARY KEY)
- `recipe_text` (TEXT) - Full recipe content
- `cuisine` (TEXT) - Cuisine type
- `time_minutes` (INTEGER) - Preparation time
- `effort_level` (TEXT) - Low/Medium/High
- `dish_preference` (TEXT) - Number of dishes
- `calories_per_serving` (INTEGER) - Target calories
- `use_external_ingredients` (BOOLEAN) - Allow non-inventory items
- `prioritize_expiring` (BOOLEAN) - Use expiring items first
- `user_prompt` (TEXT) - User's custom request
- `created_at` (TIMESTAMP) - When recipe was generated

**dietary_profiles**
- `id` (INTEGER PRIMARY KEY)
- `name` (TEXT) - Profile name (e.g., "John")
- `restrictions` (TEXT) - Dietary restrictions (e.g., "No dairy, vegetarian")
- `created_at` (TIMESTAMP)

**settings**
- `key` (TEXT PRIMARY KEY) - Setting name
- `value` (TEXT) - Setting value (JSON for complex types)
- `updated_at` (TIMESTAMP)

## Configuration Management

### Hybrid Approach (Environment + Database)

**Environment Variables** (`.env` file):
- Default values for Docker deployment
- Required: `GROCY_URL`, `GROCY_API_KEY`, `LLM_API_URL`, `LLM_API_KEY`, `LLM_MODEL`
- Optional: `MAX_RECIPE_HISTORY`, `APPRISE_URL`, `UNIT_PREFERENCE`

**Database Overrides** (`settings` table):
- Runtime configuration via UI
- Takes precedence over environment variables
- Immediate effect (no restart required)
- Managed via Settings page

**Config Manager** (`config_manager.py`):
- Merges environment variables with database overrides
- Provides `get_effective_config()` function
- Used by all API endpoints

## API Endpoints

### Recipe Generation
- `POST /api/recipes/generate` - Generate new recipe
- `POST /api/recipes/{id}/regenerate` - Regenerate existing recipe
- `GET /api/recipes/history` - Get recipe history
- `DELETE /api/recipes/{id}` - Delete recipe

### Recipe Integration (v1.1)
- `POST /api/recipes/{id}/parse-ingredients` - Parse recipe ingredients for review
- `POST /api/recipes/{id}/save-to-grocy-reviewed` - Save reviewed recipe to Grocy

### Inventory Management (v1.1)
- `POST /api/inventory/parse` - Parse text into inventory items
- `POST /api/inventory/purchase` - Add items to Grocy stock
- `POST /api/inventory/consume` - Remove items from Grocy stock
- `POST /api/inventory/add-to-shopping-list` - Add items to Grocy shopping list

### Dietary Profiles
- `GET /api/profiles/` - List all profiles
- `POST /api/profiles/` - Create profile
- `PUT /api/profiles/{id}` - Update profile
- `DELETE /api/profiles/{id}` - Delete profile

### Settings & Testing
- `GET /api/settings/config` - Get current configuration
- `POST /api/settings/config` - Update configuration
- `GET /api/settings/test/grocy` - Test Grocy connection
- `GET /api/settings/test/llm` - Test LLM connection
- `POST /api/settings/setup-unit-conversions` - Setup kitchen units (v1.1)
- `POST /api/settings/grocy/setup-locations` - Setup storage locations (v1.1)

## Key Features

### Recipe Generation
- **Inventory-Aware**: Uses Grocy stock data
- **Customizable Parameters**: Cuisine, time, effort, servings, calories, etc.
- **Elzar Personality**: Toggle between entertaining and professional
- **Dietary Restrictions**: Profile-based restriction management
- **Smart Prompting**: Separates "From Pantry" and "Missing / To Buy" ingredients

### Inventory Manager (v1.1)
- **Bulk Parsing**: Paste receipts or ingredient lists
- **AI Matching**: LLM matches text to Grocy products
- **Purchase/Consume**: Add or remove from stock
- **Auto-Creation**: Creates missing products and units
- **Manual Review**: Edit before committing

### Recipe Integration (v1.1)
- **Consume Ingredients**: Mark recipe ingredients as consumed
  - Stock checking before consume
  - Clear error messages for insufficient stock
  - Manual review and editing
- **Shopping List**: Add missing ingredients
  - Only adds items not in stock or insufficient
  - Converts to realistic purchasing quantities
  - Shows "nothing to add" if fully stocked
- **Save to Grocy**: Store recipe in Grocy database
  - Links ingredients to products
  - Clean formatting (no Elzar flair)
  - Creates missing products/units

### Settings & Setup (v1.1)
- **Connection Testing**: Verify Grocy and LLM APIs
- **Unit Setup**: One-click creation of 30+ kitchen units and 50+ conversions
- **Location Setup**: One-click creation of Pantry and Fridge
- **Unit Preference**: Choose metric or imperial
- **UI Configuration**: Edit API keys and URLs without .env file

## LLM Integration

### Prompts

**Recipe Generation** (`llm_client.py`):
- Includes inventory list with quantities
- Dietary restrictions from active profiles
- User preferences (cuisine, time, effort, etc.)
- Elzar personality toggle
- Structured output format (calories | servings | prep time)
- Ingredient separation (From Pantry vs Missing / To Buy)

**Inventory Parsing** (`inventory_matcher.py`):
- Parses unstructured text (receipts, lists)
- Matches to existing Grocy products
- Suggests quantities and units
- Assigns confidence levels (high/medium/low/new)
- Suggests storage locations

**Recipe Ingredient Extraction** (`inventory_matcher.py`):
- Extracts ingredients from recipe text
- Matches to Grocy products
- Converts quantities to appropriate units
- For shopping list: converts to purchasing quantities

### LLM Providers Supported
- OpenRouter (recommended for Gemini)
- OpenAI
- Ollama (local)
- Any OpenAI-compatible API

## Grocy Integration

### API Operations

**Read Operations**:
- `get_stock()` - Current inventory
- `get_products()` - All products
- `get_locations()` - Storage locations
- `get_quantity_units()` - Units and conversions
- `format_inventory_for_llm()` - Formatted for AI

**Write Operations**:
- `purchase_product()` - Add stock
- `consume_product()` - Remove stock
- `add_to_shopping_list()` - Add shopping list item
- `create_product()` - Create new product
- `create_quantity_unit()` - Create new unit
- `create_unit_conversion()` - Create conversion
- `create_location()` - Create storage location
- `create_recipe()` - Create recipe entity
- `add_recipe_ingredient()` - Link ingredient to recipe

### Stock Management
- Checks stock before consuming
- Shows clear error messages
- Handles unit conversions
- Supports multiple locations

## Deployment

### Systemd Services

**elzar-backend.service**:
- Runs FastAPI with Uvicorn
- Auto-restart on failure
- Starts on boot
- Logs to journalctl

**elzar-frontend.service**:
- Runs Vite dev server with --host
- Auto-restart on failure
- Starts on boot
- Accessible on port 5173

### Setup Script (`setup.sh`)

**Bootstrap Phase**:
- Detects if running as root
- Installs system dependencies (git, python3, nodejs, npm)
- Supports Debian/Ubuntu and RHEL/CentOS/Fedora

**Setup Phase**:
- Creates Python virtual environment
- Installs Python dependencies
- Installs Node.js dependencies
- Creates data directory
- Copies .env.example to .env

**Service Installation**:
- Copies systemd service files
- Enables services
- Starts services

### One-Command Deployment
```bash
ssh root@YOUR_LXC_IP "apt update && apt install -y git && \
  git clone https://github.com/ShigglesAndGits/elzar-recipe-generator.git && \
  cd elzar-recipe-generator && \
  bash setup.sh"
```

## Development Phases

### Phase 1: Core Functionality ✅
- Basic recipe generation
- Grocy inventory integration
- Simple UI with customization options
- Recipe history

### Phase 2: Enhanced Features ✅
- Dietary profile management
- UI-based configuration
- Connection testing
- Elzar personality toggle

### Phase 3: Inventory Management (v1.1) ✅
- Bulk inventory parsing
- AI-powered product matching
- Purchase/consume operations
- Auto-creation of products/units

### Phase 4: Recipe Integration (v1.1) ✅
- Consume recipe ingredients
- Add missing to shopping list
- Save recipe to Grocy
- Ingredient review workflow

### Phase 5: Setup Automation (v1.1) ✅
- One-click unit setup
- One-click location setup
- Improved error messages
- Stock checking

### Phase 6: Polish & Optimization (Planned)
- Kiosk mode for touchscreen
- Mobile-optimized UI
- Docker Compose deployment
- Performance optimization

### Phase 7: Advanced Features (Planned)
- Recipe notifications
- Meal planning calendar
- Nutrition tracking
- Recipe rating system

## Future Enhancements

### High Priority
- [ ] Docker Compose deployment
- [ ] Kiosk mode UI
- [ ] Mobile-responsive design
- [ ] Recipe notifications via Apprise

### Medium Priority
- [ ] Meal planning calendar
- [ ] Recipe rating and favorites
- [ ] Nutrition tracking
- [ ] Multi-language support

### Low Priority
- [ ] Recipe sharing
- [ ] Community recipe database
- [ ] Voice control integration
- [ ] Grocery delivery integration

## Known Issues & Limitations

### Current Limitations
- Single-user system (no authentication)
- Requires Grocy instance
- Requires LLM API access
- No offline mode
- English only

### Known Issues
- None currently reported

## Testing

### Manual Testing Checklist
- [ ] Recipe generation with various parameters
- [ ] Dietary profile creation and toggling
- [ ] Inventory parsing (receipts, lists)
- [ ] Consume ingredients workflow
- [ ] Shopping list workflow
- [ ] Save recipe workflow
- [ ] Unit and location setup
- [ ] Configuration changes
- [ ] Connection testing
- [ ] Recipe history browsing

### Test Data
- Sample Grocy inventory
- Sample dietary restrictions
- Sample shopping receipts
- Sample ingredient lists

## Documentation

- **README.md**: User-facing documentation
- **PROJECT_PLAN.md**: This file - technical overview
- **PROJECT_PLAN_V1.1.md**: v1.1 feature specification
- **DEVELOPMENT.md**: Development notes and history
- **Code Comments**: Inline documentation
- **API Docstrings**: FastAPI auto-generated docs at `/docs`

## Contributing

### Code Style
- Python: PEP 8, type hints
- JavaScript: ESLint, Prettier
- React: Functional components, hooks
- CSS: Tailwind utility classes

### Git Workflow
- Feature branches
- Descriptive commit messages
- Pull requests for review

### Testing
- Manual testing required
- Document test scenarios
- Report bugs via GitHub issues

## License

MIT License - See LICENSE file for details

---

*Made with ❤️ and a dash of BAM! 🌶️*

**Version**: 1.1.0  
**Last Updated**: November 2025  
**Status**: Production Ready
