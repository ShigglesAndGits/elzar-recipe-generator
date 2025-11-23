# Elzar - Quick Start Guide 🌶️

Welcome to Elzar! Let's get you up and running quickly.

## Prerequisites Checklist

Before starting, make sure you have:

- [ ] Python 3.8 or higher installed
- [ ] Node.js 16 or higher installed (optional for frontend development)
- [ ] A running Grocy instance
- [ ] Grocy API key
- [ ] An LLM API key (OpenRouter, OpenAI, or local model endpoint)

## Step-by-Step Setup

### 1. Backend Setup (5 minutes)

```bash
# Navigate to backend directory
cd backend

# Create a Python virtual environment
python3 -m venv venv

# Activate the virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Create your configuration file
cp .env.example .env

# Edit .env with your actual values
nano .env  # or use your preferred editor
```

**Required .env values:**
- `GROCY_URL` - Your Grocy instance URL (e.g., https://groceries.bironfamily.net)
- `GROCY_API_KEY` - Get this from Grocy Settings → API Keys
- `LLM_API_KEY` - Your OpenRouter/OpenAI/etc API key
- `LLM_MODEL` - The model to use (e.g., `google/gemini-2.0-flash-exp:free`)

### 2. Start the Backend

```bash
# Still in backend directory with venv activated
python -m app.main
```

You should see:
```
🌶️  Elzar backend started! BAM!
📊 Database initialized at: ../data/recipes.db
```

Backend is now running at `http://localhost:8000`

Test it by visiting: `http://localhost:8000/health`

### 3. Frontend Setup (5 minutes)

Open a **new terminal window**:

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start the development server
npm run dev
```

Frontend will start at `http://localhost:5173`

### 4. First Time Setup in the App

1. **Open your browser** to `http://localhost:5173`

2. **Test Connections** (Settings page):
   - Go to Settings
   - Click "Test Connection" for Grocy
   - Click "Test Connection" for LLM
   - Both should show ✓ Success

3. **Create Dietary Profiles** (optional):
   - Go to Profiles page
   - Add household members with dietary restrictions
   - Example: "John - Gluten-free, lactose intolerant"

4. **Generate Your First Recipe**:
   - Go to Generator page
   - Select your preferences
   - Press the big **🌶️ BAM!** button
   - Wait 10-30 seconds
   - Enjoy your recipe!

## Troubleshooting

### Backend Issues

**Error: "ModuleNotFoundError"**
- Make sure your virtual environment is activated
- Run `pip install -r requirements.txt` again

**Error: "Failed to connect to Grocy"**
- Check that `GROCY_URL` is correct in `.env`
- Verify your Grocy instance is running and accessible
- Test the URL in your browser
- Check that `GROCY_API_KEY` is valid

**Error: "Failed to connect to LLM"**
- Verify `LLM_API_KEY` is correct
- Check that `LLM_API_URL` is correct
- For OpenRouter: Make sure you have credits
- For local models: Ensure the model is running

### Frontend Issues

**Error: "npm: command not found"**
- Install Node.js from https://nodejs.org/

**Error: "Failed to fetch" when generating recipe**
- Make sure backend is running
- Check that backend is at `http://localhost:8000`
- Look at browser console (F12) for detailed errors

**Blank page or React errors**
- Clear your browser cache
- Try `npm install` again
- Check for errors in terminal

## Usage Tips

### For Best Results

1. **Keep Grocy inventory updated** - The more accurate your inventory, the better the recipes
2. **Use dietary profiles** - They help the AI understand your needs
3. **Be specific in additional notes** - "I'm craving comfort food" or "Something quick and easy"
4. **Prioritize expiring ingredients** - Reduce food waste!
5. **Try regenerate** - If you don't like the first recipe, regenerate for a different one

### Kiosk Mode (Raspberry Pi)

If setting up on a Raspberry Pi for fridge mounting:

1. Access Elzar from your Pi browser: `http://your-server-ip:5173`
2. Go to Settings
3. Enable "Kiosk Mode"
4. Interface will optimize for touchscreen
5. Set up Chromium kiosk mode (see README.md for details)

## Next Steps

- [ ] Set up notification service for sending recipes to your phone
- [ ] Configure max recipe history if you want more/less than 1000
- [ ] Explore different cuisines and preferences
- [ ] Share the app with your household

## Getting Help

- Check the main `README.md` for detailed documentation
- Review `PROJECT_PLAN.md` for feature roadmap
- API docs available at `http://localhost:8000/docs`

## Quick Commands Reference

**Backend:**
```bash
cd backend
source venv/bin/activate
python -m app.main
```

**Frontend:**
```bash
cd frontend
npm run dev
```

**View Backend API Docs:**
Open `http://localhost:8000/docs` in browser

---

**BAM!** You're all set! Happy cooking! 🌶️

