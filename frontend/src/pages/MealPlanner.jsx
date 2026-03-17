import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  generateMealPlan,
  getAllProfiles,
  regenerateMealPlanRecipe,
  consumeMealPlanRecipeIngredients,
  addMealPlanRecipeMissingToShoppingList,
  saveMealPlanRecipeToGrocy
} from '../api';
import { useServiceStatus } from '../contexts/ServiceStatusContext';

const BUDGET_LEVELS = [
  { value: 'broke', label: "I'm Broke", emoji: '💸' },
  { value: 'dirt_cheap', label: 'Dirt Cheap', emoji: '🪙' },
  { value: 'cheap', label: 'Cheap', emoji: '💵' },
  { value: 'moderate', label: 'Moderate', emoji: '💰' },
  { value: 'high', label: 'High', emoji: '💎' },
  { value: 'luxury', label: 'Luxury', emoji: '👑' },
];

const TIME_OPTIONS = [
  { value: 'instant', label: 'Instant', time: '0 min' },
  { value: 'really_fast', label: 'Really Fast', time: '<15 min' },
  { value: 'fast', label: 'Fast', time: '<30 min' },
  { value: 'moderate', label: 'Moderate', time: '~1 hr' },
  { value: 'long', label: 'Long', time: '1-2 hr' },
  { value: 'all_day', label: 'All Day', time: '3-8 hr' },
];

// Cookie helpers
const saveToCookie = (key, value) => {
  try {
    document.cookie = `elzar_mp_${key}=${encodeURIComponent(JSON.stringify(value))}; path=/; max-age=31536000`;
  } catch (e) {
    console.error('Failed to save cookie:', e);
  }
};

const loadFromCookie = (key, defaultValue) => {
  try {
    const name = `elzar_mp_${key}=`;
    const decodedCookie = decodeURIComponent(document.cookie);
    const cookies = decodedCookie.split(';');
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.indexOf(name) === 0) {
        return JSON.parse(cookie.substring(name.length));
      }
    }
  } catch (e) {
    console.error('Failed to load cookie:', e);
  }
  return defaultValue;
};

function MealPlanner() {
  // Service status
  const { grocyConfigured } = useServiceStatus();

  // Form state with cookie persistence
  const [days, setDays] = useState(() => loadFromCookie('days', 7));
  const [people, setPeople] = useState(() => loadFromCookie('people', 2));

  const [generateBreakfast, setGenerateBreakfast] = useState(() => loadFromCookie('breakfast', true));
  const [generateLunch, setGenerateLunch] = useState(() => loadFromCookie('lunch', true));
  const [generateDinner, setGenerateDinner] = useState(() => loadFromCookie('dinner', true));
  const [generateSnacks, setGenerateSnacks] = useState(() => loadFromCookie('snacks', false));

  const [budgetLevel, setBudgetLevel] = useState(() => loadFromCookie('budget', 'moderate'));
  const [dailyCalorieTarget, setDailyCalorieTarget] = useState(() => loadFromCookie('calories', ''));

  const [breakfastTime, setBreakfastTime] = useState(() => loadFromCookie('bTime', 'really_fast'));
  const [lunchTime, setLunchTime] = useState(() => loadFromCookie('lTime', 'fast'));
  const [dinnerTime, setDinnerTime] = useState(() => loadFromCookie('dTime', 'moderate'));
  const [snackTime, setSnackTime] = useState(() => loadFromCookie('sTime', 'instant'));

  const [varietyLevel, setVarietyLevel] = useState(() => loadFromCookie('variety', 3));

  const [profiles, setProfiles] = useState([]);
  const [activeProfiles, setActiveProfiles] = useState(() => loadFromCookie('profiles', []));
  const [useInventory, setUseInventory] = useState(() => loadFromCookie('useInventory', true));
  const [prioritizeExpiring, setPrioritizeExpiring] = useState(() => loadFromCookie('prioritize', false));
  const [userPrompt, setUserPrompt] = useState('');

  // Plan state
  const [currentPlan, setCurrentPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedRecipe, setExpandedRecipe] = useState(null);

  // Recipe action states
  const [regeneratingRecipe, setRegeneratingRecipe] = useState(null);
  const [grocyActionLoading, setGrocyActionLoading] = useState(null);
  const [actionResult, setActionResult] = useState(null);

  // Load profiles
  useEffect(() => {
    loadProfiles();
  }, []);

  // Save to cookies
  useEffect(() => { saveToCookie('days', days); }, [days]);
  useEffect(() => { saveToCookie('people', people); }, [people]);
  useEffect(() => { saveToCookie('breakfast', generateBreakfast); }, [generateBreakfast]);
  useEffect(() => { saveToCookie('lunch', generateLunch); }, [generateLunch]);
  useEffect(() => { saveToCookie('dinner', generateDinner); }, [generateDinner]);
  useEffect(() => { saveToCookie('snacks', generateSnacks); }, [generateSnacks]);
  useEffect(() => { saveToCookie('budget', budgetLevel); }, [budgetLevel]);
  useEffect(() => { saveToCookie('calories', dailyCalorieTarget); }, [dailyCalorieTarget]);
  useEffect(() => { saveToCookie('bTime', breakfastTime); }, [breakfastTime]);
  useEffect(() => { saveToCookie('lTime', lunchTime); }, [lunchTime]);
  useEffect(() => { saveToCookie('dTime', dinnerTime); }, [dinnerTime]);
  useEffect(() => { saveToCookie('sTime', snackTime); }, [snackTime]);
  useEffect(() => { saveToCookie('variety', varietyLevel); }, [varietyLevel]);
  useEffect(() => { saveToCookie('profiles', activeProfiles); }, [activeProfiles]);
  useEffect(() => { saveToCookie('useInventory', useInventory); }, [useInventory]);
  useEffect(() => { saveToCookie('prioritize', prioritizeExpiring); }, [prioritizeExpiring]);

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
        days,
        people,
        generate_breakfast: generateBreakfast,
        generate_lunch: generateLunch,
        generate_dinner: generateDinner,
        generate_snacks: generateSnacks,
        budget_level: budgetLevel,
        daily_calorie_target: dailyCalorieTarget ? parseInt(dailyCalorieTarget) : null,
        breakfast_effort: breakfastTime,
        lunch_effort: lunchTime,
        dinner_effort: dinnerTime,
        snack_effort: snackTime,
        variety_level: varietyLevel,
        active_profiles: activeProfiles,
        // Only use inventory if Grocy is configured
        use_inventory: grocyConfigured ? useInventory : false,
        prioritize_expiring: grocyConfigured ? prioritizeExpiring : false,
        user_prompt: userPrompt || null,
      };

      const plan = await generateMealPlan(params);
      setCurrentPlan(plan);
      setExpandedRecipe(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate meal plan. This may take a while for large plans.');
      console.error('Generation error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setCurrentPlan(null);
    setError(null);
    setExpandedRecipe(null);
    setActionResult(null);
  };

  // Extract the numeric recipe ID from the compound ID (e.g., "day1_dinner_5" -> 5)
  const getNumericRecipeId = (recipeId) => {
    const parts = recipeId.split('_');
    return parseInt(parts[parts.length - 1]);
  };

  // Regenerate a single recipe
  const handleRegenerateRecipe = async (recipe) => {
    const numericId = getNumericRecipeId(recipe.id);
    setRegeneratingRecipe(recipe.id);
    setActionResult(null);

    try {
      const newRecipe = await regenerateMealPlanRecipe(currentPlan.id, numericId);

      // Update the plan with the new recipe
      setCurrentPlan(prev => ({
        ...prev,
        recipes: prev.recipes.map(r =>
          r.id === recipe.id ? { ...newRecipe, id: recipe.id } : r
        ),
        // Recalculate total cost
        estimated_total_cost: prev.recipes.reduce((sum, r) => {
          if (r.id === recipe.id) {
            return sum + (newRecipe.estimated_cost || 0);
          }
          return sum + (r.estimated_cost || 0);
        }, 0) || null
      }));

      setActionResult({ type: 'success', message: `Regenerated: ${newRecipe.title}` });
    } catch (err) {
      setActionResult({
        type: 'error',
        message: err.response?.data?.detail || 'Failed to regenerate recipe'
      });
    } finally {
      setRegeneratingRecipe(null);
    }
  };

  // Consume ingredients from Grocy
  const handleConsumeIngredients = async (recipe) => {
    const numericId = getNumericRecipeId(recipe.id);
    setGrocyActionLoading(`consume_${recipe.id}`);
    setActionResult(null);

    try {
      const result = await consumeMealPlanRecipeIngredients(currentPlan.id, numericId);
      const consumed = result.consumed?.length || 0;
      const skipped = result.skipped?.length || 0;
      const errors = result.errors?.length || 0;

      setActionResult({
        type: errors > 0 ? 'warning' : 'success',
        message: `Consumed ${consumed} items${skipped > 0 ? `, skipped ${skipped}` : ''}${errors > 0 ? `, ${errors} errors` : ''}`
      });
    } catch (err) {
      setActionResult({
        type: 'error',
        message: err.response?.data?.detail || 'Failed to consume ingredients'
      });
    } finally {
      setGrocyActionLoading(null);
    }
  };

  // Add missing ingredients to shopping list
  const handleAddMissing = async (recipe) => {
    const numericId = getNumericRecipeId(recipe.id);
    setGrocyActionLoading(`shopping_${recipe.id}`);
    setActionResult(null);

    try {
      const result = await addMealPlanRecipeMissingToShoppingList(currentPlan.id, numericId);
      const added = result.added?.length || 0;
      const skipped = result.skipped?.length || 0;

      setActionResult({
        type: 'success',
        message: `Added ${added} items to shopping list${skipped > 0 ? `, ${skipped} already in stock` : ''}`
      });
    } catch (err) {
      setActionResult({
        type: 'error',
        message: err.response?.data?.detail || 'Failed to add to shopping list'
      });
    } finally {
      setGrocyActionLoading(null);
    }
  };

  // Save recipe to Grocy
  const handleSaveToGrocy = async (recipe) => {
    const numericId = getNumericRecipeId(recipe.id);
    setGrocyActionLoading(`save_${recipe.id}`);
    setActionResult(null);

    try {
      const result = await saveMealPlanRecipeToGrocy(currentPlan.id, numericId);
      setActionResult({
        type: 'success',
        message: result.message || 'Recipe saved to Grocy'
      });
    } catch (err) {
      setActionResult({
        type: 'error',
        message: err.response?.data?.detail || 'Failed to save recipe to Grocy'
      });
    } finally {
      setGrocyActionLoading(null);
    }
  };

  // Group recipes by day
  const getRecipesByDay = () => {
    if (!currentPlan?.recipes) return {};
    const grouped = {};
    for (const recipe of currentPlan.recipes) {
      if (!grouped[recipe.day]) {
        grouped[recipe.day] = [];
      }
      grouped[recipe.day].push(recipe);
    }
    return grouped;
  };

  const getMealTypeOrder = (mealType) => {
    const order = { breakfast: 0, lunch: 1, snack: 2, dinner: 3 };
    return order[mealType] || 4;
  };

  const getMealTypeEmoji = (mealType) => {
    const emojis = { breakfast: '🌅', lunch: '☀️', snack: '🍿', dinner: '🌙' };
    return emojis[mealType] || '🍽️';
  };

  const getMealTypeColor = (mealType) => {
    const colors = {
      breakfast: 'bg-yellow-600',
      lunch: 'bg-orange-600',
      snack: 'bg-purple-600',
      dinner: 'bg-blue-600',
    };
    return colors[mealType] || 'bg-gray-600';
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Control Panel */}
      <div className="space-y-6">
        <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
          <h2 className="text-2xl font-bold mb-4 flex items-center">
            <span className="text-3xl mr-2">📅</span>
            Meal Planner
          </h2>

          {/* Days Slider */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">
              Plan Duration: {days} day{days !== 1 ? 's' : ''}
            </label>
            <input
              type="range"
              min="1"
              max="14"
              value={days}
              onChange={(e) => setDays(parseInt(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-400">
              <span>1 day</span>
              <span>1 week</span>
              <span>2 weeks</span>
            </div>
          </div>

          {/* Number of People */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">
              Number of People: {people}
            </label>
            <input
              type="range"
              min="1"
              max="12"
              value={people}
              onChange={(e) => setPeople(parseInt(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-400">
              <span>1</span>
              <span>6</span>
              <span>12</span>
            </div>
          </div>

          {/* Meal Toggles */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Meals to Generate</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setGenerateBreakfast(!generateBreakfast)}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  generateBreakfast
                    ? 'bg-yellow-600 text-white'
                    : 'bg-gray-700 text-gray-400'
                }`}
              >
                🌅 Breakfast
              </button>
              <button
                onClick={() => setGenerateLunch(!generateLunch)}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  generateLunch
                    ? 'bg-orange-600 text-white'
                    : 'bg-gray-700 text-gray-400'
                }`}
              >
                ☀️ Lunch
              </button>
              <button
                onClick={() => setGenerateDinner(!generateDinner)}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  generateDinner
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-400'
                }`}
              >
                🌙 Dinner
              </button>
              <button
                onClick={() => setGenerateSnacks(!generateSnacks)}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  generateSnacks
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-700 text-gray-400'
                }`}
              >
                🍿 Snacks
              </button>
            </div>
          </div>

          {/* Budget Level */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Budget Level</label>
            <div className="grid grid-cols-3 gap-2">
              {BUDGET_LEVELS.map((level) => (
                <button
                  key={level.value}
                  onClick={() => setBudgetLevel(level.value)}
                  className={`px-2 py-2 rounded-lg transition-colors text-sm ${
                    budgetLevel === level.value
                      ? 'bg-elzar-orange text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {level.emoji} {level.label}
                </button>
              ))}
            </div>
          </div>

          {/* Daily Calorie Target */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Daily Calorie Target</label>
            <input
              type="number"
              value={dailyCalorieTarget}
              onChange={(e) => setDailyCalorieTarget(e.target.value)}
              placeholder="e.g., 2000 (optional)"
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 focus:ring-2 focus:ring-elzar-red"
            />
            <p className="text-xs text-gray-400 mt-1">
              Meals will help achieve this target (not necessarily add up to it)
            </p>
          </div>

          {/* Cooking Time Preferences */}
          <div className="mb-4 space-y-3">
            <label className="block text-sm font-medium">Cooking Time</label>

            {generateBreakfast && (
              <div>
                <div className="text-xs text-gray-400 mb-2">🌅 Breakfast</div>
                <div className="flex flex-wrap gap-1">
                  {TIME_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setBreakfastTime(opt.value)}
                      className={`px-2 py-1 rounded text-xs transition-colors ${
                        breakfastTime === opt.value
                          ? 'bg-yellow-600 text-white'
                          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {generateLunch && (
              <div>
                <div className="text-xs text-gray-400 mb-2">☀️ Lunch</div>
                <div className="flex flex-wrap gap-1">
                  {TIME_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setLunchTime(opt.value)}
                      className={`px-2 py-1 rounded text-xs transition-colors ${
                        lunchTime === opt.value
                          ? 'bg-orange-600 text-white'
                          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {generateDinner && (
              <div>
                <div className="text-xs text-gray-400 mb-2">🌙 Dinner</div>
                <div className="flex flex-wrap gap-1">
                  {TIME_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setDinnerTime(opt.value)}
                      className={`px-2 py-1 rounded text-xs transition-colors ${
                        dinnerTime === opt.value
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {generateSnacks && (
              <div>
                <div className="text-xs text-gray-400 mb-2">🍿 Snacks</div>
                <div className="flex flex-wrap gap-1">
                  {TIME_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setSnackTime(opt.value)}
                      className={`px-2 py-1 rounded text-xs transition-colors ${
                        snackTime === opt.value
                          ? 'bg-purple-600 text-white'
                          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Variety Level */}
          <div className="mb-4">
            <div className="flex justify-between text-sm mb-1">
              <span className="font-medium">Variety Level</span>
              <span className="text-gray-400">
                {varietyLevel === 1 && 'Reuse ingredients'}
                {varietyLevel === 2 && 'Efficient shopping'}
                {varietyLevel === 3 && 'Balanced'}
                {varietyLevel === 4 && 'Diverse meals'}
                {varietyLevel === 5 && 'Maximum variety'}
              </span>
            </div>
            <input
              type="range"
              min="1"
              max="5"
              value={varietyLevel}
              onChange={(e) => setVarietyLevel(parseInt(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-400">
              <span>🔄 Repeat meals OK</span>
              <span>🌈 Unique meals</span>
            </div>
          </div>

          {/* Dietary Profiles */}
          {profiles.length > 0 && (
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Dietary Restrictions</label>
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

          {/* Inventory Options - only show when Grocy is configured */}
          {grocyConfigured && (
            <div className="mb-4 space-y-2">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useInventory}
                  onChange={(e) => setUseInventory(e.target.checked)}
                  className="w-5 h-5 rounded"
                />
                <span>Use Grocy inventory</span>
              </label>

              {useInventory && (
                <label className="flex items-center space-x-2 cursor-pointer ml-6">
                  <input
                    type="checkbox"
                    checked={prioritizeExpiring}
                    onChange={(e) => setPrioritizeExpiring(e.target.checked)}
                    className="w-5 h-5 rounded"
                  />
                  <span>Prioritize expiring ingredients</span>
                </label>
              )}
            </div>
          )}

          {/* Additional Notes */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Additional Notes</label>
            <textarea
              value={userPrompt}
              onChange={(e) => setUserPrompt(e.target.value)}
              placeholder="Any special requests..."
              rows="2"
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 focus:ring-2 focus:ring-elzar-red"
            />
          </div>

          {/* Action Buttons */}
          <div className="space-y-2">
            <button
              onClick={handleGenerate}
              disabled={loading || (!generateBreakfast && !generateLunch && !generateDinner && !generateSnacks)}
              className="w-full bg-elzar-red hover:bg-red-600 disabled:bg-gray-600 text-white font-bold py-4 px-6 rounded-lg text-xl transition-colors"
            >
              {loading ? '🔥 Planning...' : '📅 Generate Meal Plan'}
            </button>

            {currentPlan && !loading && (
              <button
                onClick={handleClear}
                className="w-full bg-gray-700 hover:bg-gray-600 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
              >
                Clear Plan
              </button>
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

      {/* Meal Plan Display */}
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
        <h2 className="text-2xl font-bold mb-4">Meal Plan</h2>

        {loading && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4 animate-bounce">📅</div>
            <p className="text-xl">Planning your meals...</p>
            <p className="text-gray-400 mt-2">This may take 1-3 minutes for larger plans</p>
          </div>
        )}

        {!loading && !currentPlan && !error && (
          <div className="text-center py-12 text-gray-400">
            <p className="text-5xl mb-4">🍽️</p>
            <p className="text-lg">No meal plan yet!</p>
            <p className="mt-2">Configure your preferences and generate a plan</p>
          </div>
        )}

        {!loading && currentPlan && (
          <div className="space-y-4">
            {/* Overview */}
            {currentPlan.overview && (
              <div className="bg-gray-700 rounded-lg p-4 mb-4">
                <h3 className="font-semibold mb-2 text-elzar-orange">Overview</h3>
                <p className="text-sm text-gray-300">{currentPlan.overview}</p>
              </div>
            )}

            {/* Stats */}
            <div className="flex flex-wrap gap-4 text-sm text-gray-400 mb-4">
              <span>📅 {currentPlan.total_days} days</span>
              <span>👥 {currentPlan.total_people} people</span>
              {currentPlan.estimated_total_cost && (
                <span className="text-green-400 font-medium">
                  💰 Est. Total: ${currentPlan.estimated_total_cost.toFixed(2)}
                </span>
              )}
              <span>🍽️ {currentPlan.recipes.length} recipes</span>
            </div>

            {/* Action Result Notification */}
            {actionResult && (
              <div
                className={`mb-4 p-3 rounded-lg text-sm ${
                  actionResult.type === 'success'
                    ? 'bg-green-900 border border-green-700 text-green-200'
                    : actionResult.type === 'warning'
                    ? 'bg-yellow-900 border border-yellow-700 text-yellow-200'
                    : 'bg-red-900 border border-red-700 text-red-200'
                }`}
              >
                <div className="flex justify-between items-center">
                  <span>{actionResult.message}</span>
                  <button
                    onClick={() => setActionResult(null)}
                    className="ml-2 text-gray-400 hover:text-white"
                  >
                    ✕
                  </button>
                </div>
              </div>
            )}

            {/* Recipes by Day */}
            {Object.entries(getRecipesByDay())
              .sort(([a], [b]) => parseInt(a) - parseInt(b))
              .map(([day, recipes]) => (
                <div key={day} className="border border-gray-700 rounded-lg overflow-hidden">
                  <div className="bg-gray-700 px-4 py-2 font-semibold">
                    Day {day}
                  </div>
                  <div className="divide-y divide-gray-700">
                    {recipes
                      .sort((a, b) => getMealTypeOrder(a.meal_type) - getMealTypeOrder(b.meal_type))
                      .map((recipe) => (
                        <div key={recipe.id} className="p-4">
                          <div
                            className="flex items-center justify-between cursor-pointer"
                            onClick={() => setExpandedRecipe(expandedRecipe === recipe.id ? null : recipe.id)}
                          >
                            <div className="flex items-center gap-3">
                              <span className={`${getMealTypeColor(recipe.meal_type)} px-2 py-1 rounded text-xs uppercase font-semibold`}>
                                {getMealTypeEmoji(recipe.meal_type)} {recipe.meal_type}
                              </span>
                              <span className="font-medium">{recipe.title}</span>
                            </div>
                            <div className="flex items-center gap-4 text-sm text-gray-400">
                              {recipe.estimated_cost && (
                                <span className="text-green-400">${recipe.estimated_cost.toFixed(2)}</span>
                              )}
                              {recipe.calories_estimate && (
                                <span>{recipe.calories_estimate} cal</span>
                              )}
                              {recipe.prep_time_minutes && (
                                <span>{recipe.prep_time_minutes} min</span>
                              )}
                              <span className="text-xl">
                                {expandedRecipe === recipe.id ? '▼' : '▶'}
                              </span>
                            </div>
                          </div>

                          {expandedRecipe === recipe.id && (
                            <div className="mt-4 pt-4 border-t border-gray-700">
                              <div className="prose prose-invert prose-sm max-w-none">
                                <ReactMarkdown>{recipe.recipe_text}</ReactMarkdown>
                              </div>

                              {/* Recipe Actions */}
                              <div className="mt-4 pt-4 border-t border-gray-700 flex flex-wrap gap-2">
                                {/* Regenerate button - always available */}
                                <button
                                  className="text-xs bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-600 text-white px-3 py-1 rounded transition-colors"
                                  disabled={regeneratingRecipe === recipe.id}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleRegenerateRecipe(recipe);
                                  }}
                                >
                                  {regeneratingRecipe === recipe.id ? '🔄 Regenerating...' : '🔄 Regenerate'}
                                </button>

                                {/* Grocy integration buttons - only show when configured */}
                                {grocyConfigured && (
                                  <>
                                    <button
                                      className="text-xs bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 text-white px-3 py-1 rounded transition-colors"
                                      disabled={grocyActionLoading === `consume_${recipe.id}`}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleConsumeIngredients(recipe);
                                      }}
                                    >
                                      {grocyActionLoading === `consume_${recipe.id}` ? '⏳...' : '🍽️ Consume'}
                                    </button>
                                    <button
                                      className="text-xs bg-cyan-600 hover:bg-cyan-700 disabled:bg-gray-600 text-white px-3 py-1 rounded transition-colors"
                                      disabled={grocyActionLoading === `shopping_${recipe.id}`}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleAddMissing(recipe);
                                      }}
                                    >
                                      {grocyActionLoading === `shopping_${recipe.id}` ? '⏳...' : '🛒 Add Missing'}
                                    </button>
                                    <button
                                      className="text-xs bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-3 py-1 rounded transition-colors"
                                      disabled={grocyActionLoading === `save_${recipe.id}`}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleSaveToGrocy(recipe);
                                      }}
                                    >
                                      {grocyActionLoading === `save_${recipe.id}` ? '⏳...' : '💾 Save to Grocy'}
                                    </button>
                                  </>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                  </div>
                </div>
              ))}

            {/* Plan Metadata */}
            <div className="mt-6 pt-4 border-t border-gray-700 text-sm text-gray-400">
              <p>Generated: {new Date(currentPlan.created_at).toLocaleString()}</p>
              {currentPlan.llm_model && <p>Model: {currentPlan.llm_model}</p>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default MealPlanner;
