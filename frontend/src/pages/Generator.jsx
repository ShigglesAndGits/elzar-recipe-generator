import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import GrocyActionModal from '../components/GrocyActionModal';
import RecipeIngredientReview from '../components/RecipeIngredientReview';
import { useServiceStatus } from '../contexts/ServiceStatusContext';
import {
  generateRecipe,
  regenerateRecipe,
  getAllProfiles,
  downloadRecipe,
  sendRecipeNotification,
  consumeRecipeIngredients,
  addMissingToShoppingList,
  saveRecipeToGrocy,
  parseRecipeIngredients,
  getAdvice
} from '../api';

const CUISINES = [
  'No Preference',
  'American',
  'Asian (General)',
  'BBQ / Grilling',
  'British',
  'Cajun / Creole',
  'Caribbean',
  'Chinese',
  'Ethiopian',
  'French',
  'German',
  'Greek',
  'Indian',
  'Italian',
  'Japanese',
  'Korean',
  'Mediterranean',
  'Mexican',
  'Middle Eastern',
  'Moroccan',
  'Soul Food',
  'Southern',
  'Spanish',
  'Thai',
  'Vietnamese',
];

const KITCHEN_EQUIPMENT = [
  'Oven',
  'Stovetop',
  'Microwave',
  'Air Fryer',
  'Instant Pot',
  'Slow Cooker',
  'Electric Kettle',
  'Grill',
  'Toaster Oven',
  'Sous Vide',
  'Blender',
  'Food Processor',
];

// Cookie helpers
const saveToCookie = (key, value) => {
  try {
    document.cookie = `elzar_${key}=${encodeURIComponent(JSON.stringify(value))}; path=/; max-age=31536000`; // 1 year
  } catch (e) {
    console.error('Failed to save cookie:', e);
  }
};

const loadFromCookie = (key, defaultValue) => {
  try {
    const name = `elzar_${key}=`;
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

function Generator() {
  // Service status
  const { grocyConfigured } = useServiceStatus();

  // Form state with cookie persistence
  const [cuisine, setCuisine] = useState(() => loadFromCookie('cuisine', 'No Preference'));
  const [profiles, setProfiles] = useState([]);
  const [activeProfiles, setActiveProfiles] = useState(() => loadFromCookie('activeProfiles', []));
  const [prioritizeExpiring, setPrioritizeExpiring] = useState(() => loadFromCookie('prioritizeExpiring', false));
  const [timeMinutes, setTimeMinutes] = useState(() => loadFromCookie('timeMinutes', 60));
  const [effortLevel, setEffortLevel] = useState(() => loadFromCookie('effortLevel', 'Medium'));
  const [dishPreference, setDishPreference] = useState(() => loadFromCookie('dishPreference', "I don't care"));
  const [caloriesPerServing, setCaloriesPerServing] = useState(() => loadFromCookie('caloriesPerServing', ''));
  const [useExternalIngredients, setUseExternalIngredients] = useState(() => loadFromCookie('useExternalIngredients', false));
  const [elzarVoice, setElzarVoice] = useState(() => loadFromCookie('elzarVoice', false)); // OFF by default
  const [servings, setServings] = useState(() => loadFromCookie('servings', '3-4'));
  const [bulkPrep, setBulkPrep] = useState(() => loadFromCookie('bulkPrep', false));
  const [highLeftoverPotential, setHighLeftoverPotential] = useState(() => loadFromCookie('highLeftoverPotential', false));
  const [availableEquipment, setAvailableEquipment] = useState(() => loadFromCookie('availableEquipment', KITCHEN_EQUIPMENT)); // All checked by default
  const [equipmentExpanded, setEquipmentExpanded] = useState(false);
  const [userPrompt, setUserPrompt] = useState('');

  // Recipe state
  const [currentRecipe, setCurrentRecipe] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Modal state for Grocy actions
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [modalResults, setModalResults] = useState(null);
  const [modalActionType, setModalActionType] = useState(null);

  // Review modal state
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewParsedItems, setReviewParsedItems] = useState(null);
  const [reviewActionType, setReviewActionType] = useState(null);

  // Advice state
  const [adviceQuestion, setAdviceQuestion] = useState('');
  const [adviceResponse, setAdviceResponse] = useState(null);
  const [adviceLoading, setAdviceLoading] = useState(false);

  // Load profiles on mount
  useEffect(() => {
    loadProfiles();
  }, []);

  // Save settings to cookies when they change
  useEffect(() => { saveToCookie('cuisine', cuisine); }, [cuisine]);
  useEffect(() => { saveToCookie('activeProfiles', activeProfiles); }, [activeProfiles]);
  useEffect(() => { saveToCookie('prioritizeExpiring', prioritizeExpiring); }, [prioritizeExpiring]);
  useEffect(() => { saveToCookie('timeMinutes', timeMinutes); }, [timeMinutes]);
  useEffect(() => { saveToCookie('effortLevel', effortLevel); }, [effortLevel]);
  useEffect(() => { saveToCookie('dishPreference', dishPreference); }, [dishPreference]);
  useEffect(() => { saveToCookie('caloriesPerServing', caloriesPerServing); }, [caloriesPerServing]);
  useEffect(() => { saveToCookie('useExternalIngredients', useExternalIngredients); }, [useExternalIngredients]);
  useEffect(() => { saveToCookie('elzarVoice', elzarVoice); }, [elzarVoice]);
  useEffect(() => { saveToCookie('servings', servings); }, [servings]);
  useEffect(() => { saveToCookie('bulkPrep', bulkPrep); }, [bulkPrep]);
  useEffect(() => { saveToCookie('highLeftoverPotential', highLeftoverPotential); }, [highLeftoverPotential]);
  useEffect(() => { saveToCookie('availableEquipment', availableEquipment); }, [availableEquipment]);

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

  const toggleEquipment = (equipment) => {
    setAvailableEquipment((prev) =>
      prev.includes(equipment)
        ? prev.filter((e) => e !== equipment)
        : [...prev, equipment]
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
        bulk_prep: bulkPrep,
        high_leftover_potential: highLeftoverPotential,
        available_equipment: availableEquipment,
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

  const handleAskAdvice = async () => {
    if (!adviceQuestion.trim()) return;

    setAdviceLoading(true);
    setAdviceResponse(null);

    try {
      const response = await getAdvice(
        adviceQuestion,
        activeProfiles,
        elzarVoice,
        true // include inventory
      );
      setAdviceResponse(response);
    } catch (err) {
      setAdviceResponse({
        question: adviceQuestion,
        advice: `Error: ${err.response?.data?.detail || 'Failed to get advice. Please try again.'}`,
        llm_model: 'error'
      });
      console.error('Advice error:', err);
    } finally {
      setAdviceLoading(false);
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

    try {
      // Parse ingredients first
      const parsed = await parseRecipeIngredients(currentRecipe.id, 'consume');
      
      // Show review modal
      setReviewParsedItems(parsed.parsed_items);
      setReviewActionType('consume');
      setReviewOpen(true);
    } catch (err) {
      console.error('Parse error:', err);
      alert(err.response?.data?.detail || 'Failed to parse ingredients');
    }
  };

  const handleAddMissingToShoppingList = async () => {
    if (!currentRecipe) return;

    try {
      // Parse ingredients first - use shopping mode for realistic quantities
      const parsed = await parseRecipeIngredients(currentRecipe.id, 'shopping');
      
      // Check if there are any items to add
      if (!parsed.parsed_items || parsed.parsed_items.length === 0) {
        alert('🎉 Great news! All ingredients are already in stock with sufficient quantities. Nothing to add to the shopping list!');
        return;
      }
      
      // Show review modal
      setReviewParsedItems(parsed.parsed_items);
      setReviewActionType('shopping');
      setReviewOpen(true);
    } catch (err) {
      console.error('Parse error:', err);
      alert(err.response?.data?.detail || 'Failed to parse ingredients');
    }
  };

  const handleSaveRecipeToGrocy = async () => {
    if (!currentRecipe) return;

    try {
      // Parse ingredients first
      const parsed = await parseRecipeIngredients(currentRecipe.id, 'save');
      
      // Show review modal
      setReviewParsedItems(parsed.parsed_items);
      setReviewActionType('save');
      setReviewOpen(true);
    } catch (err) {
      console.error('Parse error:', err);
      alert(err.response?.data?.detail || 'Failed to parse ingredients');
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Control Panel */}
      <div className="space-y-6">
        <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
          <h2 className="text-2xl font-bold mb-4">
            Recipe Controls
          </h2>

          {/* Spice Weasel Toggle */}
          <button
            onClick={() => setElzarVoice(!elzarVoice)}
            className={`w-full mb-6 py-4 px-4 rounded-xl font-bold transition-all shadow-lg flex flex-col items-center gap-2 ${
              elzarVoice
                ? 'bg-gradient-to-br from-purple-600 via-elzar-red to-orange-500 text-white ring-4 ring-elzar-red/50 scale-[1.02]'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600 hover:scale-[1.01]'
            }`}
          >
            <img
              src="/spice-weasel.webp"
              alt="Spice Weasel"
              className={`h-20 w-20 object-contain transition-all ${
                elzarVoice ? 'drop-shadow-[0_0_8px_rgba(239,68,68,0.7)]' : 'opacity-40 grayscale'
              }`}
            />
            <span className="text-lg">
              {elzarVoice ? 'BAM! Spice Weasel: ON' : 'Spice Weasel: OFF'}
            </span>
            <span className={`text-xs ${elzarVoice ? 'text-white/80' : 'text-gray-500'}`}>
              {elzarVoice ? 'Elzar voice enabled' : 'Click to add some flavor'}
            </span>
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
            {grocyConfigured && (
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={prioritizeExpiring}
                  onChange={(e) => setPrioritizeExpiring(e.target.checked)}
                  className="w-5 h-5 rounded"
                />
                <span>Prioritize expiring ingredients</span>
              </label>
            )}

            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={useExternalIngredients}
                onChange={(e) => setUseExternalIngredients(e.target.checked)}
                className="w-5 h-5 rounded"
              />
              <span>{grocyConfigured ? 'Use ingredients not in inventory' : 'Allow any ingredients'}</span>
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

          {/* Kitchen Equipment */}
          <div className="mb-4">
            <button
              type="button"
              onClick={() => setEquipmentExpanded(!equipmentExpanded)}
              className="w-full flex items-center justify-between bg-gray-700 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded-lg transition-colors"
            >
              <span>🍳 Kitchen Equipment ({availableEquipment.length}/{KITCHEN_EQUIPMENT.length})</span>
              <span className="text-xl">{equipmentExpanded ? '▼' : '▶'}</span>
            </button>
            
            {equipmentExpanded && (
              <div className="mt-3 p-4 bg-gray-800 rounded-lg border border-gray-700">
                <p className="text-sm text-gray-400 mb-3">Select available equipment:</p>
                <div className="grid grid-cols-2 gap-2">
                  {KITCHEN_EQUIPMENT.map((equipment) => (
                    <label
                      key={equipment}
                      className="flex items-center space-x-2 text-sm cursor-pointer hover:bg-gray-700 p-2 rounded"
                    >
                      <input
                        type="checkbox"
                        checked={availableEquipment.includes(equipment)}
                        onChange={() => toggleEquipment(equipment)}
                        className="form-checkbox h-4 w-4 text-blue-600"
                      />
                      <span>{equipment}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
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
            <div className="grid grid-cols-5 gap-2">
              {['1-2', '3-4', '5-6', '7+'].map((s) => (
                <button
                  key={s}
                  onClick={() => { setServings(s); setBulkPrep(false); }}
                  className={`px-2 py-2 rounded-lg transition-colors text-sm font-medium ${
                    servings === s && !bulkPrep
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {s}
                </button>
              ))}
              <button
                onClick={() => { setBulkPrep(true); setServings('8+'); }}
                className={`px-2 py-2 rounded-lg transition-colors text-sm font-medium ${
                  bulkPrep
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                🧊 Bulk
              </button>
            </div>
            {bulkPrep && (
              <p className="text-xs text-purple-300 mt-2">
                Bulk Prep: Recipe will freeze well in single-serving portions and reheat easily from frozen.
              </p>
            )}
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
              className="w-full bg-elzar-red hover:bg-red-600 disabled:bg-gray-600 text-white font-bold py-4 px-6 rounded-lg text-xl transition-colors flex items-center justify-center gap-2"
            >
              {loading ? (
                <>🔥 Cooking...</>
              ) : (
                <>
                  <img src="/elzar.png" alt="" className="h-7 w-7 object-contain" />
                  BAM!
                </>
              )}
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

                {/* Grocy Integration Buttons - only show when Grocy is configured */}
                {grocyConfigured && (
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
                )}
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
            <img src="/elzar.png" alt="Elzar" className="h-24 w-24 object-contain mx-auto mb-4 animate-bounce" />
            <p className="text-xl">Cooking up something amazing...</p>
            <p className="text-gray-400 mt-2">This may take 10-30 seconds</p>
          </div>
        )}

        {!loading && !currentRecipe && !error && (
          <div className="text-center py-12 text-gray-400">
            <img src="/elzar.png" alt="Elzar" className="h-20 w-20 object-contain mx-auto mb-4 opacity-50" />
            <p className="text-lg">No recipe yet!</p>
            <p className="mt-2">Press BAM! to generate a delicious recipe</p>
          </div>
        )}

        {!loading && currentRecipe && (
          <div className="recipe-content prose prose-invert max-w-none">
            <ReactMarkdown>{currentRecipe.recipe_text}</ReactMarkdown>

            <div className="mt-6 pt-4 border-t border-gray-700 text-sm text-gray-400">
              <div className="flex flex-wrap gap-4 mb-2">
                {currentRecipe.estimated_cost && (
                  <span className="text-green-400 font-medium">
                    💰 Est. Cost: ${currentRecipe.estimated_cost.toFixed(2)}
                  </span>
                )}
                {currentRecipe.calories_per_serving && (
                  <span>🔥 {currentRecipe.calories_per_serving} cal/serving</span>
                )}
                {currentRecipe.time_minutes && (
                  <span>⏱️ {currentRecipe.time_minutes} min</span>
                )}
              </div>
              <p>Generated: {new Date(currentRecipe.created_at).toLocaleString()}</p>
              {currentRecipe.llm_model && <p>Model: {currentRecipe.llm_model}</p>}
            </div>
          </div>
        )}
      </div>

      {/* Ask Elzar - Advice Section */}
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
        <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
          <img src="/elzar.png" alt="Elzar" className="h-8 w-8 object-contain" />
          Ask Elzar
        </h2>
        <p className="text-gray-400 text-sm mb-4">
          Got a cooking question? Ask for advice about techniques, substitutions, what to do with ingredients, and more.
        </p>

        <div className="space-y-3">
          <textarea
            value={adviceQuestion}
            onChange={(e) => setAdviceQuestion(e.target.value)}
            placeholder="e.g., What can I make with leftover rice? How do I know when chicken is done? What's a good substitute for eggs in baking?"
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 focus:ring-2 focus:ring-elzar-orange resize-none"
            rows="3"
            disabled={adviceLoading}
          />
          <button
            onClick={handleAskAdvice}
            disabled={adviceLoading || !adviceQuestion.trim()}
            className="w-full bg-elzar-orange hover:bg-orange-600 disabled:bg-gray-600 text-white font-bold py-3 px-6 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {adviceLoading ? (
              <>🤔 Thinking...</>
            ) : (
              <>
                <img src="/elzar.png" alt="" className="h-6 w-6 object-contain" />
                Get Advice
              </>
            )}
          </button>
        </div>

        {/* Advice Response */}
        {adviceResponse && (
          <div className="mt-4 pt-4 border-t border-gray-700">
            <div className="bg-gray-700 rounded-lg p-4">
              <p className="text-sm text-gray-400 mb-2">
                <strong>Q:</strong> {adviceResponse.question}
              </p>
              <div className="prose prose-invert max-w-none text-gray-200">
                <ReactMarkdown>{adviceResponse.advice}</ReactMarkdown>
              </div>
              {adviceResponse.llm_model && adviceResponse.llm_model !== 'error' && (
                <p className="text-xs text-gray-500 mt-3">Model: {adviceResponse.llm_model}</p>
              )}
            </div>
            <button
              onClick={() => {
                setAdviceResponse(null);
                setAdviceQuestion('');
              }}
              className="mt-2 text-sm text-gray-400 hover:text-white transition-colors"
            >
              Clear response
            </button>
          </div>
        )}
      </div>

      {/* Grocy Action Results Modal */}
      <GrocyActionModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={modalTitle}
        results={modalResults}
        actionType={modalActionType}
      />

      {/* Recipe Ingredient Review Modal */}
      <RecipeIngredientReview
        isOpen={reviewOpen}
        onClose={() => {
          setReviewOpen(false);
          setReviewParsedItems(null);
        }}
        recipeId={currentRecipe?.id}
        parsedItems={reviewParsedItems}
        actionType={reviewActionType}
        onComplete={(result) => {
          setReviewOpen(false);
          setModalTitle(
            reviewActionType === 'consume' ? 'Consume Recipe Ingredients' :
            reviewActionType === 'shopping' ? 'Add Missing to Shopping List' :
            'Save Recipe to Grocy'
          );
          setModalResults(result);
          setModalActionType(reviewActionType);
          setModalOpen(true);
        }}
      />
    </div>
  );
}

export default Generator;

