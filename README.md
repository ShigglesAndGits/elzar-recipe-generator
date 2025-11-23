# Elzar 🌶️ - Grocy Recipe Generator

**BAM!** Generate amazing recipes from your Grocy inventory using AI!

Elzar is a self-hosted web application that connects to your [Grocy](https://grocy.info/) instance and uses LLM AI to generate creative, personalized recipes based on what ingredients you have available.

## Features

✨ **Smart Recipe Generation**
- Generate recipes based on your actual Grocy inventory
- OpenAI-compatible API support (OpenRouter, Gemini, local models)
- Prioritize expiring ingredients to reduce food waste

👥 **Dietary Profiles**
- Create profiles for household members with dietary restrictions
- Toggle which members are eating to customize recipes
- Supports allergies, intolerances, and dietary preferences

🎛️ **Flexible Controls**
- Cuisine selection (Mexican, Asian, Thai, Japanese, Chinese, Italian, Indian, etc.)
- Time range slider (15-180 minutes)
- Effort level (Low/Medium/High)
- Dish cleanup preference
- Target calories per serving
- Option to use ingredients not in your fridge

📖 **Recipe History**
- Browse past recipes with filtering
- Filter by cuisine, time, effort, calories
- Search full recipe text
- Keep last 1000 recipes (configurable)

📱 **Kiosk & Mobile**
- Kiosk mode optimized for Raspberry Pi 7" touchscreen (800x480)
- Mobile-friendly responsive design
- Download recipes as text files
- Send recipes to phone via Apprise notifications

## Screenshots

*Coming soon!*

## Tech Stack

**Backend:**
- FastAPI (Python)
- SQLite database
- httpx for async API calls
- Apprise for notifications

**Frontend:**
- React 18
- Vite
- Tailwind CSS
- React Router
- React Markdown

## Prerequisites

- Python 3.8+
- Node.js 16+ (for frontend development)
- A running [Grocy](https://grocy.info/) instance with API access
- An OpenAI-compatible LLM API (OpenRouter, local Ollama, etc.)

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd grocy-recipe-generator-custom
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings (Grocy URL, API keys, etc.)

# Run the backend
python -m app.main
```

Backend will start at `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run the frontend
npm run dev
```

Frontend will start at `http://localhost:5173`

### 4. Access the Application

Open your browser to `http://localhost:5173` and press **BAM!** to generate your first recipe!

## Configuration

### Backend Configuration (.env)

```bash
# Grocy Configuration
GROCY_URL=https://groceries.bironfamily.net
GROCY_API_KEY=your_grocy_api_key_here

# LLM Configuration (OpenAI-compatible)
LLM_API_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your_api_key_here
LLM_MODEL=google/gemini-2.0-flash-exp:free

# Application Settings
MAX_RECIPE_HISTORY=1000
DATABASE_PATH=../data/recipes.db
RECIPE_EXPORT_PATH=../data/recipes

# Notification (Optional - Apprise URL)
APPRISE_URL=pbul://your_pushbullet_key

# Server
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
```

### Getting API Keys

**Grocy API Key:**
1. Log into your Grocy instance
2. Go to Settings → API Keys
3. Create a new API key

**LLM API Key (OpenRouter example):**
1. Sign up at [OpenRouter](https://openrouter.ai/)
2. Generate an API key
3. Choose a model (e.g., `google/gemini-2.0-flash-exp:free`)

**Apprise Notifications (Optional):**
- See [Apprise documentation](https://github.com/caronc/apprise) for supported services
- Example for Pushbullet: `pbul://your_access_token`
- Example for Telegram: `tgram://bot_token/chat_id`

## Docker Deployment

*Docker support coming in Phase 9!*

## Usage Guide

### Creating Dietary Profiles

1. Navigate to **Profiles** page
2. Click **+ Add Profile**
3. Enter household member's name
4. Describe their dietary restrictions (e.g., "Gluten-free, lactose intolerant")
5. Click **Create**

### Generating a Recipe

1. Go to **Generator** page
2. Select cuisine preference
3. Toggle household members who will be eating
4. Adjust time, effort, and dish preferences
5. Optionally set target calories
6. Press **🌶️ BAM!**
7. Wait 10-30 seconds for your recipe

### Managing Recipe History

1. Go to **History** page
2. Use filters to find specific recipes
3. Click a recipe to view details
4. Download or delete recipes as needed

### Kiosk Mode (Raspberry Pi)

1. Go to **Settings** page
2. Enable **Kiosk Mode** toggle
3. Interface will optimize for touchscreen
4. Larger buttons and simplified navigation

## Raspberry Pi Setup

For a fridge-mounted kiosk:

1. Install Raspberry Pi OS
2. Install Chromium browser
3. Set up autostart in kiosk mode:

```bash
# Edit autostart
nano ~/.config/lxsession/LXDE-pi/autostart

# Add these lines:
@chromium-browser --kiosk --incognito http://your-server-ip:5173
@xset s off
@xset -dpms
@xset s noblank
```

4. Enable kiosk mode in Elzar settings

## API Documentation

Once the backend is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development

### Project Structure

```
grocy-recipe-generator-custom/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── routers/      # API endpoints
│   │   ├── services/     # Grocy, LLM, notification services
│   │   └── utils/        # Helper functions
│   └── requirements.txt
├── frontend/             # React frontend
│   └── src/
│       ├── pages/        # Page components
│       ├── components/   # Reusable components
│       └── api.js        # API client
├── data/                 # Database and exported recipes
└── PROJECT_PLAN.md       # Development roadmap
```

### Running Tests

*Test suite coming soon!*

## Future Features

- [ ] Save recipes directly to Grocy
- [ ] Add missing ingredients to Grocy shopping list
- [ ] Mark recipe ingredients as consumed in Grocy
- [ ] Recipe favorites and ratings
- [ ] Export recipe history as JSON/CSV
- [ ] Voice input for kiosk mode
- [ ] Multi-language support

## Troubleshooting

**Backend won't start:**
- Check that all environment variables are set in `.env`
- Ensure Grocy URL is accessible
- Verify API keys are correct

**No recipes generating:**
- Test connections in Settings page
- Check backend logs for errors
- Verify LLM API has credits/quota

**Kiosk mode not working:**
- Clear browser cache
- Check localStorage in browser dev tools
- Refresh the page after enabling

## Contributing

Contributions welcome! Please feel free to submit issues or pull requests.

## License

MIT License - See LICENSE file for details

## Credits

Created with ❤️ and 🌶️

Inspired by the amazing [Grocy](https://grocy.info/) project.

---

**BAM!** Let's kick it up a notch! 🌶️

