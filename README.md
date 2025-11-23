# Elzar - AI-Powered Recipe Generator 🌶️

*"BAM! Let's kick it up a notch!"*

Elzar is a self-hosted web application that generates creative recipes based on your [Grocy](https://grocy.info/) inventory using AI. Named after the famous chef from Futurama, Elzar brings personality and intelligence to your kitchen!

![Version](https://img.shields.io/badge/version-1.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.9+-blue)
![React](https://img.shields.io/badge/react-18+-61dafb)

## ✨ Features

### 🍳 Recipe Generation
- **Smart Inventory Integration**: Automatically pulls available ingredients from Grocy
- **AI-Powered Creativity**: Uses OpenAI-compatible LLMs (OpenRouter, Ollama, etc.) to generate unique recipes
- **Customizable Parameters**:
  - Cuisine type (Mexican, Asian, Thai, Japanese, Chinese, Italian, or no preference)
  - Preparation time slider
  - Effort level (hands-on time)
  - Number of dishes preference
  - Target calories per serving
  - Serving size (1-2, 3-4, 5-6, 7+ for meal prep)
  - High leftover potential toggle
  - Option to use ingredients not in your fridge

### 🎭 Elzar's Personality
- **"Spice Weasel" Toggle**: Enable/disable Elzar's entertaining voice
  - **ON**: Recipes come with Elzar's signature flair and personality
  - **OFF**: Clean, professional recipe format (ingredients + instructions only)
- Recipes include calorie counts, servings, and prep time at the top

### 🥗 Dietary Management
- **User Profiles**: Create profiles for household members with dietary restrictions
- **Toggle-Based Selection**: Enable/disable profiles to include their restrictions in recipe generation
- Restrictions are automatically fed to the AI for safe, appropriate recipes

### 📦 Inventory Manager (v1.1)
- **Bulk Import**: Paste shopping receipts or ingredient lists
- **AI Parsing**: Automatically matches items to Grocy products
- **Smart Actions**:
  - **Purchase**: Add items to Grocy inventory
  - **Consume**: Remove items from Grocy inventory
  - **Auto-create**: Automatically create missing products and units
- **Manual Review**: Edit quantities, units, and product matches before committing

### 🛒 Recipe Integration (v1.1)
Three powerful buttons on every generated recipe:

1. **🔥 Consume Recipe Ingredients**
   - Marks ingredients as consumed in Grocy
   - Checks stock levels before consuming
   - Shows clear errors for insufficient stock
   - Manual review before committing changes

2. **🛒 Add Missing to Shopping List**
   - Intelligently adds only missing/insufficient ingredients
   - Converts recipe quantities to realistic purchasing amounts
   - Skips items already in stock
   - Shows "nothing to add" if fully stocked

3. **💾 Save Recipe to Grocy**
   - Saves recipe with proper formatting (no Elzar flair)
   - Links ingredients to Grocy products
   - Creates missing products/units as needed
   - Stores in Grocy's recipe database

### ⚙️ Settings & Configuration
- **Hybrid Configuration**: Environment variables for Docker, UI overrides for runtime
- **Connection Testing**: Test Grocy and LLM connections before use
- **Unit Preference**: Choose metric or imperial measurements
- **One-Click Setup**:
  - **Kitchen Units & Conversions**: Creates 30+ common units and 50+ conversions
  - **Storage Locations**: Sets up Pantry and Fridge locations
- **API Configuration**: Edit Grocy URL/Key, LLM URL/Key/Model via UI

### 📜 Recipe History
- Browse previously generated recipes
- Regenerate recipes with one click
- View recipe metadata (cuisine, time, effort, etc.)
- Persistent storage in SQLite

### 📱 Notifications (Planned)
- Send recipes to your phone via Apprise
- Support for multiple notification services

## 🏗️ Architecture

### Tech Stack
- **Backend**: FastAPI (Python 3.9+)
- **Frontend**: React 18 + Vite + Tailwind CSS
- **Database**: SQLite
- **LLM Integration**: OpenAI-compatible API client
- **Grocy Integration**: Comprehensive API wrapper
- **Deployment**: Systemd services, Docker-ready

### Project Structure
```
elzar-recipe-generator/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── config.py                  # Environment configuration
│   │   ├── models.py                  # Pydantic models
│   │   ├── database.py                # SQLite operations
│   │   ├── routers/
│   │   │   ├── recipes.py             # Recipe generation & integration
│   │   │   ├── inventory.py           # Inventory management (v1.1)
│   │   │   ├── history.py             # Recipe history
│   │   │   ├── profiles.py            # Dietary profiles
│   │   │   └── settings.py            # Settings & testing
│   │   ├── services/
│   │   │   ├── grocy_client.py        # Grocy API client
│   │   │   ├── llm_client.py          # LLM client
│   │   │   ├── inventory_matcher.py   # AI-powered inventory parsing
│   │   │   └── notification.py        # Apprise integration
│   │   └── utils/
│   │       └── config_manager.py      # Hybrid config management
│   ├── requirements.txt
│   └── .env                           # Environment variables
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Generator.jsx          # Main recipe generation page
│   │   │   ├── InventoryManager.jsx   # Bulk inventory management
│   │   │   ├── History.jsx            # Recipe history browser
│   │   │   ├── Profiles.jsx           # Dietary profile management
│   │   │   └── Settings.jsx           # Settings & configuration
│   │   ├── components/
│   │   │   ├── RecipeIngredientReview.jsx  # Ingredient review modal
│   │   │   └── GrocyActionModal.jsx        # Action result display
│   │   ├── api.js                     # Backend API client
│   │   └── App.jsx                    # Main app & routing
│   ├── package.json
│   └── vite.config.js
├── data/
│   └── recipes.db                     # SQLite database
├── setup.sh                           # Automated setup script
├── elzar-backend.service              # Systemd service (backend)
├── elzar-frontend.service             # Systemd service (frontend)
├── PROJECT_PLAN.md                    # Original project plan
├── PROJECT_PLAN_V1.1.md               # v1.1 feature plan
└── README.md                          # This file
```

## 🚀 Quick Start

### Prerequisites
- Debian/Ubuntu Linux (or similar)
- [Grocy](https://grocy.info/) instance with API access
- OpenAI-compatible LLM API (OpenRouter, Ollama, etc.)

### One-Command Setup (Fresh Debian LXC)

1. **On your LXC console**, add your SSH public key:
```bash
mkdir -p ~/.ssh
echo "YOUR_SSH_PUBLIC_KEY" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

2. **From your workstation**, run:
```bash
ssh root@YOUR_LXC_IP "apt update && apt install -y git && \
  git clone https://github.com/ShigglesAndGits/elzar-recipe-generator.git && \
  cd elzar-recipe-generator && \
  bash setup.sh"
```

3. **Configure environment variables**:
```bash
ssh root@YOUR_LXC_IP
cd elzar-recipe-generator/backend
nano .env
```

Add your configuration:
```env
# Grocy Configuration
GROCY_URL=https://your-grocy-instance.com
GROCY_API_KEY=your_grocy_api_key

# LLM Configuration
LLM_API_URL=https://openrouter.ai/api/v1/chat/completions
LLM_API_KEY=your_llm_api_key
LLM_MODEL=google/gemini-2.0-flash-exp:free

# Optional
MAX_RECIPE_HISTORY=50
APPRISE_URL=
UNIT_PREFERENCE=imperial
```

4. **Start services**:
```bash
systemctl start elzar-backend
systemctl start elzar-frontend
systemctl enable elzar-backend
systemctl enable elzar-frontend
```

5. **Access Elzar**:
   - Open browser to `http://YOUR_LXC_IP:5173`
   - Go to Settings → Test connections
   - Click "Setup Storage Locations" (creates Pantry & Fridge)
   - Click "Setup All Kitchen Units & Conversions"
   - Start generating recipes!

## 📖 Usage Guide

### First-Time Setup

1. **Settings Page**:
   - Test Grocy and LLM connections
   - Set unit preference (metric/imperial)
   - Click "Setup Storage Locations"
   - Click "Setup All Kitchen Units & Conversions"

2. **Dietary Profiles** (optional):
   - Create profiles for household members
   - Add dietary restrictions (e.g., "No dairy", "Vegetarian")
   - Toggle profiles on/off when generating recipes

3. **Generate Your First Recipe**:
   - Elzar automatically pulls your Grocy inventory
   - Adjust cuisine, time, effort, servings, etc.
   - Toggle "Spice Weasel" for Elzar's personality
   - Click "BAM!" to generate

### Using Inventory Manager

Perfect for adding groceries after shopping:

1. Go to **Inventory** page
2. Paste your shopping receipt or ingredient list
3. Select **Purchase** or **Consume**
4. Click **Parse & Match**
5. Review matched items (edit quantities/units if needed)
6. Check "Auto-create" for new products
7. Click **Purchase All** or **Consume All**

### Recipe Actions

After generating a recipe:

- **Consume Ingredients**: Removes used ingredients from Grocy
- **Add Missing to Shopping List**: Adds only what you need to buy
- **Save Recipe to Grocy**: Stores recipe in Grocy's database

All actions include a review step where you can:
- Edit quantities and units
- Match to different Grocy products
- Auto-create missing products
- See what will happen before committing

## 🔧 Configuration

### Environment Variables (.env)
```env
# Required
GROCY_URL=https://your-grocy-instance.com
GROCY_API_KEY=your_api_key
LLM_API_URL=https://api.openai.com/v1/chat/completions
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-4

# Optional
MAX_RECIPE_HISTORY=50              # Number of recipes to keep
APPRISE_URL=                       # Notification service URL
UNIT_PREFERENCE=imperial           # imperial or metric
```

### UI Configuration
Settings can be overridden via the Settings page:
- Grocy URL and API Key
- LLM API URL, Key, and Model
- Unit preference
- Max recipe history

Changes take effect immediately without restart.

## 🐛 Troubleshooting

### Backend Not Starting
```bash
# Check logs
journalctl -u elzar-backend -n 50

# Check if port 8000 is in use
ss -tulpn | grep 8000

# Restart service
systemctl restart elzar-backend
```

### Frontend Not Accessible
```bash
# Check logs
journalctl -u elzar-frontend -n 50

# Ensure Vite is running with --host
# Check frontend.log
tail -f /root/elzar-recipe-generator/frontend.log
```

### "Location does not exist" Errors
- Go to Settings → Click "Setup Storage Locations"
- This creates Pantry and Fridge in Grocy

### "Unit conversion" Errors
- Go to Settings → Click "Setup All Kitchen Units & Conversions"
- This creates 30+ units and 50+ conversions in Grocy

### LLM Not Responding
- Test connection in Settings page
- Check API key and URL
- Verify model name is correct
- Check backend logs for detailed errors

## 🎯 Roadmap

### Completed ✅
- [x] Basic recipe generation
- [x] Grocy inventory integration
- [x] Dietary profile management
- [x] UI-based configuration
- [x] Recipe history
- [x] Bulk inventory management (v1.1)
- [x] Recipe integration (consume, shopping list, save) (v1.1)
- [x] Unit and location setup automation (v1.1)

### Planned 🚧
- [ ] Kiosk mode for Raspberry Pi touchscreen
- [ ] Mobile-optimized UI
- [ ] Recipe notifications via Apprise
- [ ] Docker Compose deployment
- [ ] Multi-language support
- [ ] Recipe rating system
- [ ] Meal planning calendar
- [ ] Nutrition tracking

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- [Grocy](https://grocy.info/) - The amazing grocery management system
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://react.dev/) - Frontend framework
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS
- Futurama's Elzar - For the inspiration and personality

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation
- Review backend logs for detailed errors

---

*Made with ❤️ and a dash of BAM! 🌶️*
