import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { getRecipeHistory, deleteRecipe, downloadRecipe, toggleRecipeLock, toggleRecipeSave, createManualRecipe } from '../api';

function History() {
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRecipe, setSelectedRecipe] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // Create form state
  const [createText, setCreateText] = useState('');
  const [createCuisine, setCreateCuisine] = useState('');
  const [createTime, setCreateTime] = useState('');
  const [createEffort, setCreateEffort] = useState('');
  const [createCalories, setCreateCalories] = useState('');
  const [createLocked, setCreateLocked] = useState(false);
  const [createSaved, setCreateSaved] = useState(true);
  const [creating, setCreating] = useState(false);

  // Filters
  const [searchText, setSearchText] = useState('');
  const [cuisineFilter, setCuisineFilter] = useState('');
  const [minTime, setMinTime] = useState('');
  const [maxTime, setMaxTime] = useState('');
  const [effortFilter, setEffortFilter] = useState('');

  // Pagination
  const [page, setPage] = useState(0);
  const pageSize = 50;

  useEffect(() => {
    loadRecipes();
  }, [page, searchText, cuisineFilter, minTime, maxTime, effortFilter]);

  const loadRecipes = async () => {
    setLoading(true);
    try {
      const params = {
        limit: pageSize,
        offset: page * pageSize,
      };

      if (searchText) params.search_text = searchText;
      if (cuisineFilter) params.cuisine = cuisineFilter;
      if (minTime) params.min_time = parseInt(minTime);
      if (maxTime) params.max_time = parseInt(maxTime);
      if (effortFilter) params.effort_level = effortFilter;

      const data = await getRecipeHistory(params);
      setRecipes(data);
    } catch (err) {
      console.error('Failed to load recipe history:', err);
      alert('Failed to load recipe history');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (recipeId) => {
    const recipe = recipes.find(r => r.id === recipeId);
    if (recipe?.is_locked) {
      alert('This recipe is locked. Unlock it first to delete.');
      return;
    }
    if (!confirm('Are you sure you want to delete this recipe?')) return;

    try {
      await deleteRecipe(recipeId);
      loadRecipes();
      if (selectedRecipe?.id === recipeId) {
        setSelectedRecipe(null);
      }
    } catch (err) {
      console.error('Failed to delete recipe:', err);
      alert('Failed to delete recipe');
    }
  };

  const handleDownload = async (recipeId) => {
    try {
      const blob = await downloadRecipe(recipeId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `recipe_${recipeId}_${new Date().getTime()}.txt`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download error:', err);
      alert('Failed to download recipe');
    }
  };

  const handleToggleLock = async (recipeId) => {
    try {
      const result = await toggleRecipeLock(recipeId);
      // Update local state
      setRecipes(prev => prev.map(r =>
        r.id === recipeId ? { ...r, is_locked: result.is_locked } : r
      ));
      if (selectedRecipe?.id === recipeId) {
        setSelectedRecipe(prev => ({ ...prev, is_locked: result.is_locked }));
      }
    } catch (err) {
      console.error('Failed to toggle lock:', err);
      alert('Failed to toggle lock');
    }
  };

  const handleToggleSave = async (recipeId) => {
    try {
      const result = await toggleRecipeSave(recipeId);
      setRecipes(prev => prev.map(r =>
        r.id === recipeId ? { ...r, is_saved: result.is_saved } : r
      ));
      if (selectedRecipe?.id === recipeId) {
        setSelectedRecipe(prev => ({ ...prev, is_saved: result.is_saved }));
      }
    } catch (err) {
      console.error('Failed to toggle save:', err);
      alert('Failed to toggle save');
    }
  };

  const handleCreateRecipe = async (e) => {
    e.preventDefault();
    if (!createText.trim()) {
      alert('Recipe text is required');
      return;
    }
    setCreating(true);
    try {
      const newRecipe = await createManualRecipe({
        recipe_text: createText.trim(),
        cuisine: createCuisine || null,
        time_minutes: createTime ? parseInt(createTime) : null,
        effort_level: createEffort || null,
        calories_per_serving: createCalories ? parseInt(createCalories) : null,
        is_locked: createLocked,
        is_saved: createSaved,
      });
      setShowCreateForm(false);
      setCreateText('');
      setCreateCuisine('');
      setCreateTime('');
      setCreateEffort('');
      setCreateCalories('');
      setCreateLocked(false);
      setCreateSaved(true);
      loadRecipes();
      setSelectedRecipe(newRecipe);
    } catch (err) {
      console.error('Failed to create recipe:', err);
      alert(err.response?.data?.detail || 'Failed to create recipe');
    } finally {
      setCreating(false);
    }
  };

  const clearFilters = () => {
    setSearchText('');
    setCuisineFilter('');
    setMinTime('');
    setMaxTime('');
    setEffortFilter('');
    setPage(0);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Filters and List */}
      <div className="lg:col-span-1 space-y-4">
        {/* Filters */}
        <div className="bg-gray-800 rounded-lg p-4 shadow-lg">
          <h2 className="text-xl font-bold mb-4">Filters</h2>

          <div className="space-y-3">
            {/* Search */}
            <div>
              <label className="block text-sm font-medium mb-1">Search</label>
              <input
                type="text"
                value={searchText}
                onChange={(e) => {
                  setSearchText(e.target.value);
                  setPage(0);
                }}
                placeholder="Search recipes..."
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-elzar-red"
              />
            </div>

            {/* Cuisine */}
            <div>
              <label className="block text-sm font-medium mb-1">Cuisine</label>
              <select
                value={cuisineFilter}
                onChange={(e) => {
                  setCuisineFilter(e.target.value);
                  setPage(0);
                }}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-elzar-red"
              >
                <option value="">All</option>
                <option value="Mexican">Mexican</option>
                <option value="Asian (General)">Asian</option>
                <option value="Thai">Thai</option>
                <option value="Japanese">Japanese</option>
                <option value="Chinese">Chinese</option>
                <option value="Italian">Italian</option>
                <option value="Indian">Indian</option>
                <option value="Mediterranean">Mediterranean</option>
                <option value="American">American</option>
                <option value="French">French</option>
              </select>
            </div>

            {/* Time Range */}
            <div>
              <label className="block text-sm font-medium mb-1">Time (minutes)</label>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  value={minTime}
                  onChange={(e) => {
                    setMinTime(e.target.value);
                    setPage(0);
                  }}
                  placeholder="Min"
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-elzar-red"
                />
                <input
                  type="number"
                  value={maxTime}
                  onChange={(e) => {
                    setMaxTime(e.target.value);
                    setPage(0);
                  }}
                  placeholder="Max"
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-elzar-red"
                />
              </div>
            </div>

            {/* Effort */}
            <div>
              <label className="block text-sm font-medium mb-1">Effort</label>
              <select
                value={effortFilter}
                onChange={(e) => {
                  setEffortFilter(e.target.value);
                  setPage(0);
                }}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-elzar-red"
              >
                <option value="">All</option>
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
              </select>
            </div>

            <button
              onClick={clearFilters}
              className="w-full bg-gray-700 hover:bg-gray-600 text-white py-2 rounded text-sm transition-colors"
            >
              Clear Filters
            </button>
          </div>
        </div>

        {/* Recipe List */}
        <div className="bg-gray-800 rounded-lg p-4 shadow-lg">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">
              Recipes ({recipes.length})
            </h2>
            <button
              onClick={() => {
                setShowCreateForm(true);
                setSelectedRecipe(null);
              }}
              className="bg-elzar-red hover:bg-red-600 text-white px-3 py-1.5 rounded text-sm transition-colors"
            >
              + Add Recipe
            </button>
          </div>

          {loading && (
            <div className="text-center py-8 text-gray-400">
              Loading...
            </div>
          )}

          {!loading && recipes.length === 0 && (
            <div className="text-center py-8 text-gray-400">
              No recipes found
            </div>
          )}

          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {recipes.map((recipe) => (
              <div
                key={recipe.id}
                onClick={() => {
                  setSelectedRecipe(recipe);
                  setShowCreateForm(false);
                }}
                className={`p-3 rounded cursor-pointer transition-colors ${
                  selectedRecipe?.id === recipe.id
                    ? 'bg-elzar-red'
                    : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <p className="font-medium text-sm line-clamp-2">
                      {recipe.is_locked && <span title="Locked">🔒 </span>}
                      {recipe.is_saved && <span title="Saved">⭐ </span>}
                      {recipe.recipe_text.split('\n')[0].replace(/^#\s*/, '')}
                    </p>
                    <div className="flex flex-wrap gap-2 mt-2 text-xs text-gray-400">
                      {recipe.estimated_cost && (
                        <span className="bg-green-700 text-green-100 px-2 py-1 rounded">
                          ${recipe.estimated_cost.toFixed(2)}
                        </span>
                      )}
                      {recipe.cuisine && (
                        <span className="bg-gray-600 px-2 py-1 rounded">
                          {recipe.cuisine}
                        </span>
                      )}
                      {recipe.time_minutes && (
                        <span className="bg-gray-600 px-2 py-1 rounded">
                          {recipe.time_minutes}m
                        </span>
                      )}
                      {recipe.effort_level && (
                        <span className="bg-gray-600 px-2 py-1 rounded">
                          {recipe.effort_level}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(recipe.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {recipes.length === pageSize && (
            <div className="flex justify-between mt-4">
              <button
                onClick={() => setPage(Math.max(0, page - 1))}
                disabled={page === 0}
                className="bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 text-white px-4 py-2 rounded text-sm transition-colors"
              >
                Previous
              </button>
              <span className="text-sm text-gray-400 self-center">
                Page {page + 1}
              </span>
              <button
                onClick={() => setPage(page + 1)}
                className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded text-sm transition-colors"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Recipe View / Create Form */}
      <div className="lg:col-span-2 bg-gray-800 rounded-lg p-6 shadow-lg">
        {/* Manual Recipe Create Form */}
        {showCreateForm && (
          <>
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-2xl font-bold">Add Recipe</h2>
              <button
                onClick={() => setShowCreateForm(false)}
                className="bg-gray-600 hover:bg-gray-500 text-white px-4 py-2 rounded text-sm transition-colors"
              >
                Cancel
              </button>
            </div>
            <form onSubmit={handleCreateRecipe} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Recipe Text *</label>
                <textarea
                  value={createText}
                  onChange={(e) => setCreateText(e.target.value)}
                  placeholder={"# Mom's Shepherd's Pie\n\n**Ingredients:**\n- 2 lbs ground beef\n- 4 large potatoes\n- ...\n\n**Instructions:**\n1. Preheat oven to 375°F\n2. ..."}
                  rows="14"
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 focus:ring-2 focus:ring-elzar-red text-gray-200 placeholder-gray-500 font-mono text-sm"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">Supports markdown formatting</p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div>
                  <label className="block text-xs font-medium mb-1">Cuisine</label>
                  <input
                    type="text"
                    value={createCuisine}
                    onChange={(e) => setCreateCuisine(e.target.value)}
                    placeholder="e.g., Italian"
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-elzar-red"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Time (min)</label>
                  <input
                    type="number"
                    value={createTime}
                    onChange={(e) => setCreateTime(e.target.value)}
                    placeholder="e.g., 45"
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-elzar-red"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Effort</label>
                  <select
                    value={createEffort}
                    onChange={(e) => setCreateEffort(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-elzar-red"
                  >
                    <option value="">--</option>
                    <option value="Low">Low</option>
                    <option value="Medium">Medium</option>
                    <option value="High">High</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Cal/serving</label>
                  <input
                    type="number"
                    value={createCalories}
                    onChange={(e) => setCreateCalories(e.target.value)}
                    placeholder="e.g., 450"
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-elzar-red"
                  />
                </div>
              </div>

              <div className="flex items-center gap-6">
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={createLocked}
                    onChange={(e) => setCreateLocked(e.target.checked)}
                    className="rounded"
                  />
                  🔒 Lock recipe
                </label>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={createSaved}
                    onChange={(e) => setCreateSaved(e.target.checked)}
                    className="rounded"
                  />
                  ⭐ Save (protect from cleanup)
                </label>
              </div>

              <button
                type="submit"
                disabled={creating}
                className="bg-elzar-red hover:bg-red-600 disabled:bg-gray-600 text-white px-6 py-2 rounded-lg transition-colors"
              >
                {creating ? 'Creating...' : 'Create Recipe'}
              </button>
            </form>
          </>
        )}

        {/* Empty state */}
        {!showCreateForm && !selectedRecipe && (
          <div className="text-center py-12 text-gray-400">
            <p className="text-5xl mb-4">📖</p>
            <p className="text-lg">Select a recipe to view</p>
          </div>
        )}

        {/* Recipe Detail View */}
        {!showCreateForm && selectedRecipe && (
          <>
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-2xl font-bold">Recipe Details</h2>
              <div className="flex space-x-2">
                <button
                  onClick={() => handleToggleLock(selectedRecipe.id)}
                  className={`px-3 py-2 rounded text-sm transition-colors ${
                    selectedRecipe.is_locked
                      ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                      : 'bg-gray-600 hover:bg-gray-500 text-white'
                  }`}
                  title={selectedRecipe.is_locked ? 'Unlock recipe' : 'Lock recipe'}
                >
                  {selectedRecipe.is_locked ? '🔒 Locked' : '🔓 Lock'}
                </button>
                <button
                  onClick={() => handleToggleSave(selectedRecipe.id)}
                  className={`px-3 py-2 rounded text-sm transition-colors ${
                    selectedRecipe.is_saved
                      ? 'bg-amber-600 hover:bg-amber-700 text-white'
                      : 'bg-gray-600 hover:bg-gray-500 text-white'
                  }`}
                  title={selectedRecipe.is_saved ? 'Remove from saved' : 'Save recipe'}
                >
                  {selectedRecipe.is_saved ? '⭐ Saved' : '☆ Save'}
                </button>
                <button
                  onClick={() => handleDownload(selectedRecipe.id)}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm transition-colors"
                >
                  📥 Download
                </button>
                <button
                  onClick={() => handleDelete(selectedRecipe.id)}
                  disabled={selectedRecipe.is_locked}
                  className={`px-4 py-2 rounded text-sm transition-colors ${
                    selectedRecipe.is_locked
                      ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                      : 'bg-red-600 hover:bg-red-700 text-white'
                  }`}
                  title={selectedRecipe.is_locked ? 'Unlock recipe to delete' : 'Delete recipe'}
                >
                  🗑️ Delete
                </button>
              </div>
            </div>

            <div className="recipe-content prose prose-invert max-w-none">
              <ReactMarkdown>{selectedRecipe.recipe_text}</ReactMarkdown>

              <div className="mt-6 pt-4 border-t border-gray-700 text-sm text-gray-400">
                <div className="flex flex-wrap gap-4 mb-2">
                  {selectedRecipe.estimated_cost && (
                    <span className="text-green-400 font-medium">
                      💰 Est. Cost: ${selectedRecipe.estimated_cost.toFixed(2)}
                    </span>
                  )}
                  {selectedRecipe.calories_per_serving && (
                    <span>🔥 {selectedRecipe.calories_per_serving} cal/serving</span>
                  )}
                  {selectedRecipe.time_minutes && (
                    <span>⏱️ {selectedRecipe.time_minutes} min</span>
                  )}
                </div>
                {selectedRecipe.parent_recipe_id && (
                  <p className="text-blue-400">Based on recipe #{selectedRecipe.parent_recipe_id}</p>
                )}
                <p>Generated: {new Date(selectedRecipe.created_at).toLocaleString()}</p>
                {selectedRecipe.llm_model && <p>Model: {selectedRecipe.llm_model}</p>}
                {!selectedRecipe.llm_model && <p className="text-amber-400">Manually added</p>}
                {selectedRecipe.active_profiles && selectedRecipe.active_profiles !== '[]' && (
                  <p>Profiles: {JSON.parse(selectedRecipe.active_profiles).join(', ')}</p>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default History;
