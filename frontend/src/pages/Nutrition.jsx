import React, { useState, useEffect } from 'react';
import { getNutritionalOverview } from '../api';

const RATING_COLORS = {
  high: 'bg-green-500',    // 7-10
  medium: 'bg-yellow-500', // 4-6
  low: 'bg-red-500',       // 1-3
};

const getRatingColor = (rating) => {
  if (rating >= 7) return RATING_COLORS.high;
  if (rating >= 4) return RATING_COLORS.medium;
  return RATING_COLORS.low;
};

const getRatingLabel = (rating) => {
  if (rating >= 8) return 'Excellent';
  if (rating >= 6) return 'Good';
  if (rating >= 4) return 'Fair';
  if (rating >= 2) return 'Low';
  return 'Very Low';
};

function Nutrition() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(14);
  const [showRecipes, setShowRecipes] = useState(false);

  useEffect(() => {
    loadOverview();
  }, [days]);

  const loadOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getNutritionalOverview(days);
      setOverview(data);
    } catch (err) {
      console.error('Failed to load nutritional overview:', err);
      setError('Failed to load nutritional data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="animate-pulse text-4xl mb-4">📊</div>
        <p className="text-gray-400">Loading nutritional data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-red-900/50 border border-red-700 rounded-lg p-6 text-center">
          <p className="text-red-300">{error}</p>
          <button
            onClick={loadOverview}
            className="mt-3 px-4 py-2 bg-red-700 hover:bg-red-600 rounded-lg text-white text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const hasData = overview && overview.recipes_analyzed > 0;

  // Sort averages: lowest first to highlight gaps
  const sortedNutrients = hasData
    ? Object.entries(overview.averages).sort((a, b) => a[1] - b[1])
    : [];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Nutritional Dashboard</h1>
          <p className="text-gray-400 text-sm mt-1">
            How nutrient-dense are your recent meals?
          </p>
        </div>

        {/* Time period selector */}
        <div className="flex gap-1 bg-gray-800 rounded-lg p-1">
          {[7, 14, 30].map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                days === d
                  ? 'bg-elzar-red text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {!hasData ? (
        <div className="bg-gray-800 rounded-lg p-8 text-center">
          <span className="text-6xl mb-4 block">🥗</span>
          <h2 className="text-xl font-semibold mb-2">No Nutritional Data Yet</h2>
          <p className="text-gray-400 max-w-md mx-auto">
            Nutrient ratings are automatically generated when you create recipes through Chat or Quick Recipe.
            Start cooking and your nutritional profile will build up here!
          </p>
        </div>
      ) : (
        <>
          {/* Summary stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <p className="text-3xl font-bold text-white">{overview.recipes_analyzed}</p>
              <p className="text-sm text-gray-400">Recipes Analyzed</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <p className="text-3xl font-bold text-white">{days}</p>
              <p className="text-sm text-gray-400">Day Window</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <p className={`text-3xl font-bold ${overview.gaps.length > 0 ? 'text-red-400' : 'text-green-400'}`}>
                {overview.gaps.length}
              </p>
              <p className="text-sm text-gray-400">Nutritional Gaps</p>
            </div>
          </div>

          {/* Gap alerts */}
          {overview.gaps.length > 0 && (
            <div className="bg-red-900/30 border border-red-700 rounded-lg p-4">
              <h3 className="font-semibold text-red-300 mb-2">Nutritional Gaps Detected</h3>
              <p className="text-sm text-red-200 mb-3">
                These nutrients have averaged below 4/10 across your recent recipes. Consider adding meals rich in these areas.
              </p>
              <div className="flex flex-wrap gap-2">
                {overview.gaps.map(gap => (
                  <span
                    key={gap}
                    className="px-3 py-1 bg-red-900/50 border border-red-600 rounded-full text-sm text-red-200"
                  >
                    {gap}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Nutrient bars */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Nutrient Density Ratings</h2>
            <p className="text-xs text-gray-500 mb-4">
              Average rating across {overview.recipes_analyzed} recipes (1 = poor source, 10 = excellent source)
            </p>

            <div className="space-y-3">
              {sortedNutrients.map(([nutrient, avg]) => (
                <div key={nutrient} className="flex items-center gap-3">
                  <span className="text-sm text-gray-300 w-28 text-right flex-shrink-0">
                    {nutrient}
                  </span>
                  <div className="flex-1 h-6 bg-gray-700 rounded-full overflow-hidden relative">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${getRatingColor(avg)}`}
                      style={{ width: `${(avg / 10) * 100}%` }}
                    />
                    <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-white drop-shadow">
                      {avg.toFixed(1)}/10
                    </span>
                  </div>
                  <span className={`text-xs w-16 flex-shrink-0 ${
                    avg >= 7 ? 'text-green-400' : avg >= 4 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {getRatingLabel(avg)}
                  </span>
                </div>
              ))}
            </div>

            {/* Legend */}
            <div className="flex gap-4 mt-4 pt-4 border-t border-gray-700 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full bg-green-500"></span> Good (7-10)
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full bg-yellow-500"></span> Fair (4-6)
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full bg-red-500"></span> Low (1-3)
              </span>
            </div>
          </div>

          {/* Per-recipe breakdown */}
          <div className="bg-gray-800 rounded-lg p-6">
            <button
              onClick={() => setShowRecipes(!showRecipes)}
              className="flex items-center justify-between w-full text-left"
            >
              <h2 className="text-lg font-semibold">Per-Recipe Breakdown</h2>
              <span className="text-gray-400 text-sm">
                {showRecipes ? '▼ Hide' : '▶ Show'} {overview.recipes.length} recipes
              </span>
            </button>

            {showRecipes && (
              <div className="mt-4 space-y-3">
                {overview.recipes.map(recipe => (
                  <RecipeNutrientCard key={recipe.id} recipe={recipe} />
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}


function RecipeNutrientCard({ recipe }) {
  const [expanded, setExpanded] = useState(false);

  // Compute average rating for quick glance
  const ratings = Object.values(recipe.ratings || {});
  const avgRating = ratings.length > 0
    ? (ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(1)
    : 'N/A';

  return (
    <div className="bg-gray-700/50 rounded-lg p-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-3">
          <span className={`text-sm font-bold px-2 py-0.5 rounded ${
            avgRating >= 6 ? 'bg-green-900/50 text-green-400' :
            avgRating >= 4 ? 'bg-yellow-900/50 text-yellow-400' :
            'bg-red-900/50 text-red-400'
          }`}>
            {avgRating}
          </span>
          <div>
            <span className="text-sm text-white">Recipe #{recipe.id}</span>
            {recipe.cuisine && (
              <span className="text-xs text-gray-400 ml-2">{recipe.cuisine}</span>
            )}
          </div>
        </div>
        <span className="text-xs text-gray-500">
          {new Date(recipe.created_at).toLocaleDateString()}
        </span>
      </button>

      {expanded && (
        <div className="mt-3 grid grid-cols-3 sm:grid-cols-5 gap-2">
          {Object.entries(recipe.ratings || {})
            .sort((a, b) => b[1] - a[1])
            .map(([nutrient, rating]) => (
              <div
                key={nutrient}
                className={`text-center p-1.5 rounded text-xs ${
                  rating >= 7 ? 'bg-green-900/30 text-green-300' :
                  rating >= 4 ? 'bg-yellow-900/30 text-yellow-300' :
                  'bg-red-900/30 text-red-300'
                }`}
              >
                <div className="font-bold text-sm">{rating}</div>
                <div className="truncate">{nutrient}</div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}


export default Nutrition;
