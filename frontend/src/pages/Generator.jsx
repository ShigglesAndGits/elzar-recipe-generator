import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  generateRecipe, 
  regenerateRecipe, 
  getAllProfiles, 
  downloadRecipe, 
  sendRecipeNotification,
  consumeRecipeIngredients,
  addMissingToShoppingList,
  saveRecipeToGrocy
} from '../api';

const CUISINES = [
  'No Preference',
  'Mexican',
  'Asian (General)',
  'Thai',
  'Japanese',
  'Chinese',
  'Italian',
  'Indian',
  'Mediterranean',
  'American',
  'French',
];

function Generator() {
  // Form state
  const [cuisine, setCuisine] = useState('No Preference');
  const [profiles, setProfiles] = useState([]);
  const [activeProfiles, setActiveProfiles] = useState([]);
  const [prioritizeExpiring, setPrioritizeExpiring] = useState(false);
  const [timeMinutes, setTimeMinutes] = useState(60);
  const [effortLevel, setEffortLevel] = useState('Medium');
  const [dishPreference, setDishPreference] = useState("I don't care");
  const [caloriesPerServing, setCaloriesPerServing] = useState('');
  const [useExternalIngredients, setUseExternalIngredients] = useState(false);
  const [elzarVoice, setElzarVoice] = useState(true);
  const [servings, setServings] = useState('3-4');
  const [highLeftoverPotential, setHighLeftoverPotential] = useState(false);
  const [userPrompt, setUserPrompt] = useState('');

  // Recipe state
  const [currentRecipe, setCurrentRecipe] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load profiles on mount
  useEffect(() => {
    loadProfiles();
  }, []);

  const loadProfiles = async () => {
    try {
      const data = await getAllProfiles();
      setProfiles(data);
    } catch (err) {
      console.error('Failed to load profiles:', err);
    }
  };

  const toggleProfile = (profileName) => {
    setActiveProfiles((prev) =>
      prev.includes(profileName)
        ? prev.filter((n) => n !== profileName)
        : [...prev, profileName]
    );
  };

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = {
        cuisine,
        active_profiles: activeProfiles,
        prioritize_expiring: prioritizeExpiring,
        time_minutes: timeMinutes,
        effort_level: effortLevel,
        dish_preference: dishPreference,
        calories_per_serving: caloriesPerServing ? parseInt(caloriesPerServing) : null,
        use_external_ingredients: useExternalIngredients,
        elzar_voice: elzarVoice,
        servings,
        high_leftover_potential: highLeftoverPotential,
        user_prompt: userPrompt || null,
      };

      const recipe = await generateRecipe(params);
      setCurrentRecipe(recipe);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate recipe. Check your backend connection.');
      console.error('Generation error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerate = async () => {
    if (!currentRecipe) return;

    setLoading(true);
    setError(null);

    try {
      const recipe = await regenerateRecipe(currentRecipe.id);
      setCurrentRecipe(recipe);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to regenerate recipe');
      console.error('Regeneration error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setCurrentRecipe(null);
    setError(null);
  };

  const handleDownload = async () => {
    if (!currentRecipe) return;

    try {
      const blob = await downloadRecipe(currentRecipe.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `recipe_${currentRecipe.id}_${new Date().getTime()}.txt`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download error:', err);
      alert('Failed to download recipe');
    }
  };

  const handleSendToPhone = async () => {
    if (!currentRecipe) return;

    try {
      await sendRecipeNotification(currentRecipe.id);
      alert('Recipe sent to your phone! 🌶️');
    } catch (err) {
      console.error('Notification error:', err);
      alert(err.response?.data?.detail || 'Failed to send notification. Check your settings.');
    }
  };

  const handleConsumeIngredients = async () => {
    if (!currentRecipe) return;

    if (!confirm('This will consume the recipe ingredients from your Grocy stock. Continue?')) {
      return;
    }

    try {
      const result = await consumeRecipeIngredients(currentRecipe.id);
      
      let message = `✓ Consumed ${result.consumed.length} ingredients\n`;
      if (result.insufficient_stock.length > 0) {
        message += `⚠ ${result.insufficient_stock.length} items had insufficient stock\n`;
      }
      if (result.skipped.length > 0) {
        message += `⚠ Skipped ${result.skipped.length} items`;
      }
      
      alert(message);
    } catch (err) {
      console.error('Consume error:', err);
      alert(err.response?.data?.detail || 'Failed to consume ingredients');
    }
  };

  const handleAddMissingToShoppingList = async () => {
    if (!currentRecipe) return;

    try {
      const result = await addMissingToShoppingList(currentRecipe.id);
      
      if (result.added.length === 0) {
        alert('All ingredients are already in stock! 🎉');
      } else {
        let message = `✓ Added ${result.added.length} items to shopping list\n\n`;
        message += result.added.map(item => 
          `• ${item.product_name}: ${item.quantity} ${item.unit}`
        ).join('\n');
        
        if (result.skipped.length > 0) {
          message += `\n\n⚠ Skipped ${result.skipped.length} items (no product match)`;
        }
        
        alert(message);
      }
    } catch (err) {
      console.error('Shopping list error:', err);
      alert(err.response?.data?.detail || 'Failed to add to shopping list');
    }
  };

  const handleSaveRecipeToGrocy = async () => {
    if (!currentRecipe) return;

    if (!confirm('This will save the recipe to Grocy with linked ingredients. Continue?')) {
      return;
    }

    try {
      const result = await saveRecipeToGrocy(currentRecipe.id);
      
      let message = `✓ Recipe saved to Grocy!\n`;
      message += `Recipe: ${result.recipe_name}\n`;
      message += `Servings: ${result.servings}\n`;
      message += `Ingredients: ${result.ingredients_added.length} added`;
      
      if (result.ingredients_skipped.length > 0) {
        message += `\n⚠ ${result.ingredients_skipped.length} ingredients skipped (no match)`;
      }
      
      alert(message);
    } catch (err) {
      console.error('Save recipe error:', err);
      alert(err.response?.data?.detail || 'Failed to save recipe to Grocy');
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Control Panel */}
      <div className="space-y-6">
        <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
          <h2 className="text-2xl font-bold mb-4 flex items-center">
            <span className="text-3xl mr-2">🌶️</span>
            Recipe Controls
          </h2>

          <button
            onClick={() => setElzarVoice(!elzarVoice)}
            className={`w-full mb-6 py-3 px-4 rounded-lg font-bold text-lg flex items-center justify-center transition-colors shadow-md ${
              elzarVoice
                ? 'bg-gradient-to-r from-purple-600 to-elzar-red text-white ring-2 ring-elzar-red'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            {elzarVoice ? '🌶️ Hit it with the spice weasel! (ON)' : '🧂 Spice Weasel: OFF'}
          </button>

          {/* Cuisine */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Cuisine</label>
            <select
              value={cuisine}
              onChange={(e) => setCuisine(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 focus:ring-2 focus:ring-elzar-red"
            >
              {CUISINES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {/* Household Members */}
          {profiles.length > 0 && (
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Household Members (Dietary Restrictions)</label>
              <div className="grid grid-cols-2 gap-2">
                {profiles.map((profile) => (
                  <button
                    key={profile.id}
                    onClick={() => toggleProfile(profile.name)}
                    className={`px-4 py-2 rounded-lg border-2 transition-colors ${
                      activeProfiles.includes(profile.name)
                        ? 'bg-elzar-red border-elzar-red text-white'
                        : 'bg-gray-700 border-gray-600 text-gray-300 hover:border-elzar-red'
                    }`}
                  >
                    {profile.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Toggles */}
          <div className="mb-4 space-y-2">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={prioritizeExpiring}
                onChange={(e) => setPrioritizeExpiring(e.target.checked)}
                className="w-5 h-5 rounded"
              />
              <span>Prioritize expiring ingredients</span>
            </label>

            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={useExternalIngredients}
                onChange={(e) => setUseExternalIngredients(e.target.checked)}
                className="w-5 h-5 rounded"
              />
              <span>Use ingredients not in fridge</span>
            </label>

            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={highLeftoverPotential}
                onChange={(e) => setHighLeftoverPotential(e.target.checked)}
                className="w-5 h-5 rounded"
              />
              <span>High leftover potential</span>
            </label>
          </div>

          {/* Time Slider */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">
              Time: {timeMinutes} minutes
            </label>
            <input
              type="range"
              min="15"
              max="180"
              step="5"
              value={timeMinutes}
              onChange={(e) => setTimeMinutes(parseInt(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-400">
              <span>15 min</span>
              <span>180 min</span>
            </div>
          </div>

          {/* Effort Level */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Effort Level</label>
            <div className="grid grid-cols-3 gap-2">
              {['Low', 'Medium', 'High'].map((level) => (
                <button
                  key={level}
                  onClick={() => setEffortLevel(level)}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    effortLevel === level
                      ? 'bg-elzar-orange text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {level}
                </button>
              ))}
            </div>
          </div>

          {/* Servings */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Servings</label>
            <div className="grid grid-cols-4 gap-2">
              {['1-2', '3-4', '5-6', '7+'].map((s) => (
                <button
                  key={s}
                  onClick={() => setServings(s)}
                  className={`px-2 py-2 rounded-lg transition-colors text-sm font-medium ${
                    servings === s
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Dish Preference */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Dish Cleanup</label>
            <div className="grid grid-cols-3 gap-2">
              {['No dishes', 'Few dishes', "I don't care"].map((pref) => (
                <button
                  key={pref}
                  onClick={() => setDishPreference(pref)}
                  className={`px-4 py-2 rounded-lg transition-colors text-sm ${
                    dishPreference === pref
                      ? 'bg-elzar-yellow text-gray-900'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {pref}
                </button>
              ))}
            </div>
          </div>

          {/* Calories */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Target Calories (per serving)</label>
            <input
              type="number"
              value={caloriesPerServing}
              onChange={(e) => setCaloriesPerServing(e.target.value)}
              placeholder="Optional"
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 focus:ring-2 focus:ring-elzar-red"
            />
          </div>

          {/* Additional Notes */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Additional Notes (Optional)</label>
            <textarea
              value={userPrompt}
              onChange={(e) => setUserPrompt(e.target.value)}
              placeholder="Any special requests or preferences..."
              rows="3"
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 focus:ring-2 focus:ring-elzar-red"
            />
          </div>

          {/* Action Buttons */}
          <div className="space-y-2">
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="w-full bg-elzar-red hover:bg-red-600 disabled:bg-gray-600 text-white font-bold py-4 px-6 rounded-lg text-xl transition-colors"
            >
              {loading ? '🔥 Cooking...' : '🌶️ BAM!'}
            </button>

            {currentRecipe && !loading && (
              <>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={handleRegenerate}
                    className="bg-elzar-orange hover:bg-orange-600 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
                  >
                    Regenerate
                  </button>
                  <button
                    onClick={handleClear}
                    className="bg-gray-700 hover:bg-gray-600 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
                  >
                    Clear
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={handleDownload}
                    className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
                  >
                    📥 Download
                  </button>
                  <button
                    onClick={handleSendToPhone}
                    className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
                  >
                    📱 Send to Phone
                  </button>
                </div>

                {/* Grocy Integration Buttons */}
                <div className="border-t border-gray-700 pt-2 mt-2">
                  <p className="text-xs text-gray-400 mb-2">Grocy Integration</p>
                  <div className="space-y-2">
                    <button
                      onClick={handleConsumeIngredients}
                      className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors text-sm"
                    >
                      🍽️ Consume Ingredients
                    </button>
                    <button
                      onClick={handleAddMissingToShoppingList}
                      className="w-full bg-cyan-600 hover:bg-cyan-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors text-sm"
                    >
                      🛒 Add Missing to Shopping List
                    </button>
                    <button
                      onClick={handleSaveRecipeToGrocy}
                      className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors text-sm"
                    >
                      💾 Save Recipe to Grocy
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>

          {error && (
            <div className="mt-4 bg-red-900 border border-red-700 rounded-lg p-4 text-red-200">
              <p className="font-semibold">Error:</p>
              <p>{error}</p>
            </div>
          )}
        </div>
      </div>

      {/* Recipe Display */}
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
        <h2 className="text-2xl font-bold mb-4">Recipe</h2>

        {loading && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4 animate-bounce">🌶️</div>
            <p className="text-xl">Cooking up something amazing...</p>
            <p className="text-gray-400 mt-2">This may take 10-30 seconds</p>
          </div>
        )}

        {!loading && !currentRecipe && !error && (
          <div className="text-center py-12 text-gray-400">
            <p className="text-5xl mb-4">👨‍🍳</p>
            <p className="text-lg">No recipe yet!</p>
            <p className="mt-2">Press BAM! to generate a delicious recipe</p>
          </div>
        )}

        {!loading && currentRecipe && (
          <div className="recipe-content prose prose-invert max-w-none">
            <ReactMarkdown>{currentRecipe.recipe_text}</ReactMarkdown>
            
            <div className="mt-6 pt-4 border-t border-gray-700 text-sm text-gray-400">
              <p>Generated: {new Date(currentRecipe.created_at).toLocaleString()}</p>
              {currentRecipe.llm_model && <p>Model: {currentRecipe.llm_model}</p>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Generator;

