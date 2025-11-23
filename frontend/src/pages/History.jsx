import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { getRecipeHistory, deleteRecipe, downloadRecipe } from '../api';

function History() {
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRecipe, setSelectedRecipe] = useState(null);
  
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
          <h2 className="text-xl font-bold mb-4">
            Recipes ({recipes.length})
          </h2>

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
                onClick={() => setSelectedRecipe(recipe)}
                className={`p-3 rounded cursor-pointer transition-colors ${
                  selectedRecipe?.id === recipe.id
                    ? 'bg-elzar-red'
                    : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <p className="font-medium text-sm line-clamp-2">
                      {recipe.recipe_text.split('\n')[0].replace(/^#\s*/, '')}
                    </p>
                    <div className="flex flex-wrap gap-2 mt-2 text-xs text-gray-400">
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

      {/* Recipe View */}
      <div className="lg:col-span-2 bg-gray-800 rounded-lg p-6 shadow-lg">
        {!selectedRecipe && (
          <div className="text-center py-12 text-gray-400">
            <p className="text-5xl mb-4">📖</p>
            <p className="text-lg">Select a recipe to view</p>
          </div>
        )}

        {selectedRecipe && (
          <>
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-2xl font-bold">Recipe Details</h2>
              <div className="flex space-x-2">
                <button
                  onClick={() => handleDownload(selectedRecipe.id)}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm transition-colors"
                >
                  📥 Download
                </button>
                <button
                  onClick={() => handleDelete(selectedRecipe.id)}
                  className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded text-sm transition-colors"
                >
                  🗑️ Delete
                </button>
              </div>
            </div>

            <div className="recipe-content prose prose-invert max-w-none">
              <ReactMarkdown>{selectedRecipe.recipe_text}</ReactMarkdown>
              
              <div className="mt-6 pt-4 border-t border-gray-700 text-sm text-gray-400">
                <p>Generated: {new Date(selectedRecipe.created_at).toLocaleString()}</p>
                {selectedRecipe.llm_model && <p>Model: {selectedRecipe.llm_model}</p>}
                {selectedRecipe.active_profiles && (
                  <p>Dietary Profiles: {JSON.parse(selectedRecipe.active_profiles).join(', ')}</p>
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

