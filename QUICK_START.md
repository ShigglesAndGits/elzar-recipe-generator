# Elzar Quick Start Guide 🌶️

Get up and running with Elzar in minutes!

## Prerequisites

- Linux server (Debian/Ubuntu recommended)
- [Grocy](https://grocy.info/) instance with API access
- LLM API key (OpenRouter, OpenAI, or Ollama)

## Installation

### 1. SSH Key Setup

On your LXC/server console:
```bash
mkdir -p ~/.ssh
echo "YOUR_SSH_PUBLIC_KEY" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 2. One-Command Install

From your workstation:
```bash
ssh root@YOUR_SERVER_IP "apt update && apt install -y git && \
  git clone https://github.com/ShigglesAndGits/elzar-recipe-generator.git && \
  cd elzar-recipe-generator && \
  bash setup.sh"
```

### 3. Configure

SSH into your server and edit the `.env` file:
```bash
ssh root@YOUR_SERVER_IP
cd elzar-recipe-generator/backend
nano .env
```

Minimum required configuration:
```env
GROCY_URL=https://your-grocy-instance.com
GROCY_API_KEY=your_grocy_api_key
LLM_API_URL=https://openrouter.ai/api/v1/chat/completions
LLM_API_KEY=your_openrouter_api_key
LLM_MODEL=google/gemini-2.0-flash-exp:free
```

### 4. Start Services

```bash
systemctl start elzar-backend
systemctl start elzar-frontend
systemctl enable elzar-backend
systemctl enable elzar-frontend
```

### 5. Access Elzar

Open your browser to: `http://YOUR_SERVER_IP:5173`

## First-Time Setup

### Step 1: Settings Page

1. Click **Settings** in the navigation
2. Click **Test Grocy Connection** (should show ✅)
3. Click **Test LLM Connection** (should show ✅)
4. Click **📦 Setup Storage Locations** (creates Pantry & Fridge)
5. Click **🚀 Setup All Kitchen Units & Conversions** (creates 30+ units and 50+ conversions)

### Step 2: Dietary Profiles (Optional)

1. Click **Profiles** in the navigation
2. Click **Add Profile**
3. Enter name (e.g., "John")
4. Enter restrictions (e.g., "No dairy, vegetarian")
5. Click **Save**
6. Repeat for each household member

### Step 3: Generate Your First Recipe

1. Click **Generator** in the navigation
2. Elzar automatically loads your Grocy inventory
3. Adjust settings:
   - **Cuisine**: Choose a cuisine type or "No preference"
   - **Time**: How long until you want to eat
   - **Effort**: How much work you want to do
   - **Servings**: 1-2, 3-4, 5-6, or 7+ (meal prep)
   - **Calories**: Target calories per serving
   - **Spice Weasel**: Toggle Elzar's personality on/off
4. Toggle any dietary profiles you want to include
5. Click **BAM!** to generate

## Common Tasks

### Adding Groceries After Shopping

1. Go to **Inventory** page
2. Paste your shopping receipt or type items:
   ```
   2 lbs chicken breast
   1 gallon milk
   3 tomatoes
   1 lb pasta
   ```
3. Select **Purchase**
4. Click **Parse & Match**
5. Review matched items (edit if needed)
6. Check "Auto-create" for any new products
7. Click **Purchase All**

### Using a Recipe

After generating a recipe, you have three options:

**🔥 Consume Recipe Ingredients**
- Marks ingredients as consumed in Grocy
- Reviews items first (edit quantities/units)
- Shows clear errors for insufficient stock
- Updates your Grocy inventory

**🛒 Add Missing to Shopping List**
- Only adds items you don't have
- Converts to realistic purchasing amounts
- Adds to Grocy shopping list

**💾 Save Recipe to Grocy**
- Saves recipe to Grocy's recipe database
- Links ingredients to products
- Clean format (no Elzar flair)

### Browsing Recipe History

1. Click **History** in the navigation
2. Browse previously generated recipes
3. Click **Regenerate** to create a new version
4. Click **Delete** to remove from history

## Troubleshooting

### Backend Not Running

```bash
# Check status
systemctl status elzar-backend

# View logs
journalctl -u elzar-backend -n 50

# Restart
systemctl restart elzar-backend
```

### Frontend Not Accessible

```bash
# Check status
systemctl status elzar-frontend

# View logs
journalctl -u elzar-frontend -n 50

# Restart
systemctl restart elzar-frontend
```

### "Location does not exist" Errors

Go to Settings → Click "Setup Storage Locations"

### "Unit conversion" Errors

Go to Settings → Click "Setup All Kitchen Units & Conversions"

### Can't Connect to Grocy

1. Check your `GROCY_URL` in Settings
2. Verify your `GROCY_API_KEY`
3. Test connection in Settings page
4. Check Grocy is accessible from your server

### LLM Not Responding

1. Check your `LLM_API_KEY` in Settings
2. Verify your `LLM_MODEL` name is correct
3. Test connection in Settings page
4. Check backend logs for detailed errors

## Tips & Tricks

### Getting Better Recipes

- **Use the "Spice Weasel"**: Elzar's personality makes recipes more fun!
- **Be specific**: Add custom prompts like "I want something spicy" or "Make it kid-friendly"
- **Adjust servings**: Use "7+" for meal prep recipes with good leftover potential
- **Toggle profiles**: Only enable dietary restrictions for people eating the meal

### Managing Inventory

- **Paste receipts**: The AI is smart enough to parse most receipt formats
- **Edit before committing**: Always review quantities and units
- **Auto-create wisely**: Check "Auto-create" for new products, but verify the match is correct
- **Use locations**: Grocy works best when items have proper locations (Pantry vs Fridge)

### Recipe Integration

- **Review first**: Always review ingredients before consuming or adding to shopping list
- **Check stock**: The system checks stock before consuming, but verify quantities
- **Edit units**: If units don't match, edit them in the review screen
- **Save favorites**: Save recipes to Grocy for easy access later

### Configuration

- **Metric vs Imperial**: Set your preference in Settings
- **Model selection**: Try different LLM models for different results
  - Gemini: Fast and free (OpenRouter)
  - GPT-4: High quality but costs money
  - Ollama: Local and private
- **History limit**: Adjust `MAX_RECIPE_HISTORY` if you want to keep more/fewer recipes

## Next Steps

- Explore different cuisines and settings
- Create dietary profiles for your household
- Try the Inventory Manager with a shopping receipt
- Save your favorite recipes to Grocy
- Set up notifications (coming soon!)

## Need Help?

- Check the full [README.md](README.md) for detailed documentation
- Review [PROJECT_PLAN.md](PROJECT_PLAN.md) for technical details
- Open an issue on GitHub for bugs or feature requests
- Check backend logs for detailed error messages

---

*BAM! You're ready to cook! 🌶️*

