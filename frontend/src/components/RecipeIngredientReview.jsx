import React, { useState, useEffect } from 'react';
import { 
  purchaseItems, 
  consumeItems,
  addItemsToShoppingList,
  saveRecipeToGrocyReviewed
} from '../api';

function RecipeIngredientReview({ 
  isOpen, 
  onClose, 
  recipeId, 
  parsedItems, 
  actionType, // 'consume', 'shopping', or 'save'
  onComplete 
}) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);

  useEffect(() => {
    if (parsedItems) {
      setItems(parsedItems.map(item => ({
        ...item,
        selected: true, // Auto-select all items
        // For shopping list and save, default to creating missing products
        // For consume, only create if marked as 'new'
        create_if_missing: (actionType === 'shopping' || actionType === 'save') 
          ? !item.grocy_product_id 
          : item.confidence === 'new'
      })));
    }
  }, [parsedItems]);

  const handleItemChange = (index, field, value) => {
    setItems(prev => prev.map((item, i) =>
      i === index ? { ...item, [field]: value } : item
    ));
  };

  const handleToggleCreateIfMissing = (index) => {
    setItems(prev => prev.map((item, i) =>
      i === index ? { ...item, create_if_missing: !item.create_if_missing } : item
    ));
  };

  const handleExecuteAction = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const selectedItems = items.filter(item => item.selected);
      
      if (selectedItems.length === 0) {
        alert('No items selected.');
        setLoading(false);
        return;
      }

      const transactionItems = selectedItems.map(item => ({
        product_id: item.grocy_product_id,
        product_name: item.item_name,
        amount: parseFloat(item.quantity) || 1.0,
        unit: item.unit || 'unit',
        location_id: item.location_id,
        quantity_unit_id: item.quantity_unit_id,
        best_before_date: null,
        action: actionType === 'consume' ? 'consume' : 'purchase',
        create_if_missing: item.create_if_missing && !item.grocy_product_id
      }));

      let result;
      if (actionType === 'consume') {
        const rawResult = await consumeItems(transactionItems);
        // Transform to match GrocyActionModal expected format
        result = {
          consumed: rawResult.success || [],
          skipped: rawResult.failed || [],
          insufficient_stock: []
        };
      } else if (actionType === 'shopping') {
        const rawResult = await addItemsToShoppingList(transactionItems);
        // Transform to match GrocyActionModal expected format
        result = {
          added: rawResult.success || [],
          already_in_stock: [],
          skipped: rawResult.failed || [],
          created_products: rawResult.created_products || []
        };
      } else {
        // save - call the proper save recipe endpoint
        const rawResult = await saveRecipeToGrocyReviewed(recipeId, transactionItems);
        result = {
          recipe_name: rawResult.recipe_name || "Recipe",
          servings: rawResult.servings || 4,
          grocy_recipe_id: rawResult.grocy_recipe_id,
          ingredients_added: rawResult.ingredients_added || [],
          ingredients_skipped: rawResult.ingredients_skipped || [],
          created_products: rawResult.created_products || []
        };
      }

      if (onComplete) {
        onComplete(result);
      }
    } catch (err) {
      // Extract detailed error message
      let errorMessage = `Failed to ${actionType} items.`;
      
      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      console.error('Action error:', err);
      
      // Don't close the modal on error - let user see the error and retry
      setLoading(false);
      return; // Exit early, don't call onComplete
    }
    
    setLoading(false);
  };

  const toggleItemSelection = (index) => {
    setItems(prev => prev.map((item, i) =>
      i === index ? { ...item, selected: !item.selected } : item
    ));
  };

  if (!isOpen) return null;

  const getActionTitle = () => {
    switch (actionType) {
      case 'consume': return 'Consume Recipe Ingredients';
      case 'shopping': return 'Add Missing to Shopping List';
      case 'save': return 'Save Recipe to Grocy';
      default: return 'Review Ingredients';
    }
  };

  const getActionButtonText = () => {
    switch (actionType) {
      case 'consume': return 'Consume Selected';
      case 'shopping': return 'Add to Shopping List';
      case 'save': return 'Save Recipe';
      default: return 'Execute';
    }
  };

  const getConfidenceBadge = (confidence) => {
    const colors = {
      high: 'bg-green-700 text-green-200',
      medium: 'bg-yellow-700 text-yellow-200',
      low: 'bg-orange-700 text-orange-200',
      new: 'bg-red-700 text-red-200'
    };
    return colors[confidence] || colors.new;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg max-w-7xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gray-700 px-6 py-4 border-b border-gray-600">
          <h3 className="text-xl font-bold text-white">{getActionTitle()}</h3>
          <p className="text-sm text-gray-300 mt-1">
            Review and edit ingredients before proceeding
          </p>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto flex-1">
          {error && (
            <div className="bg-red-900 border border-red-700 text-red-200 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}

          {!results ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-2 px-2">Select</th>
                    <th className="text-left py-2 px-2">Ingredient</th>
                    <th className="text-left py-2 px-2">Quantity</th>
                    <th className="text-left py-2 px-2">Unit</th>
                    <th className="text-left py-2 px-2">Grocy Match</th>
                    <th className="text-left py-2 px-2">Status</th>
                    <th className="text-left py-2 px-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, index) => (
                    <tr key={index} className="border-b border-gray-700 hover:bg-gray-750">
                      <td className="py-2 px-2">
                        <input
                          type="checkbox"
                          checked={item.selected}
                          onChange={() => toggleItemSelection(index)}
                          className="form-checkbox text-elzar-red w-4 h-4"
                        />
                      </td>
                      <td className="py-2 px-2">
                        <input
                          type="text"
                          value={item.item_name}
                          onChange={(e) => handleItemChange(index, 'item_name', e.target.value)}
                          className="bg-gray-700 border border-gray-600 rounded px-2 py-1 w-full text-sm focus:ring-2 focus:ring-elzar-red"
                          placeholder="Item name"
                        />
                      </td>
                      <td className="py-2 px-2">
                        <input
                          type="number"
                          value={item.quantity}
                          onChange={(e) => handleItemChange(index, 'quantity', e.target.value)}
                          className="bg-gray-700 border border-gray-600 rounded px-2 py-1 w-20 text-sm focus:ring-2 focus:ring-elzar-red"
                          step="0.1"
                          min="0"
                        />
                      </td>
                      <td className="py-2 px-2">
                        <input
                          type="text"
                          value={item.unit}
                          onChange={(e) => handleItemChange(index, 'unit', e.target.value)}
                          className="bg-gray-700 border border-gray-600 rounded px-2 py-1 w-24 text-sm focus:ring-2 focus:ring-elzar-red"
                          placeholder="unit"
                        />
                      </td>
                      <td className="py-2 px-2">
                        {item.grocy_product_name ? (
                          <span className="text-green-400">{item.grocy_product_name}</span>
                        ) : (
                          <span className="text-yellow-400">No Match</span>
                        )}
                      </td>
                      <td className="py-2 px-2">
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${getConfidenceBadge(item.confidence)}`}>
                          {item.confidence === 'new' ? 'NEW' : item.confidence.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2 px-2">
                        {item.confidence === 'new' && !item.grocy_product_id ? (
                          <label className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={item.create_if_missing}
                              onChange={() => handleToggleCreateIfMissing(index)}
                              className="form-checkbox text-blue-600 w-4 h-4"
                            />
                            <span className="text-xs whitespace-nowrap">Auto-create</span>
                          </label>
                        ) : (
                          <span className="text-xs text-gray-500">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="mt-4 p-3 bg-gray-700 rounded-lg text-sm text-gray-300">
                <p className="font-semibold mb-1">💡 Tips:</p>
                <ul className="list-disc list-inside space-y-1 text-xs">
                  <li>Edit quantities and units directly in the table</li>
                  <li>Items marked <span className="text-red-400 font-semibold">NEW</span> will be automatically created in Grocy if "Auto-create" is checked</li>
                  <li>Uncheck items you don't want to process</li>
                </ul>
              </div>
            </div>
          ) : (
            <div className="bg-gray-700 rounded-lg p-4">
              <h4 className="font-semibold text-green-400 mb-2">✓ Action Completed!</h4>
              <p className="text-sm text-gray-300">
                Successfully processed {items.filter(i => i.selected).length} items.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-700 px-6 py-4 border-t border-gray-600 flex justify-between items-center">
          <div className="text-sm text-gray-300">
            {!results && `${items.filter(i => i.selected).length} of ${items.length} items selected`}
          </div>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="bg-gray-600 hover:bg-gray-500 text-white font-bold py-2 px-6 rounded-lg transition-colors"
            >
              {results ? 'Close' : 'Cancel'}
            </button>
            {!results && (
              <button
                onClick={handleExecuteAction}
                disabled={loading || items.filter(i => i.selected).length === 0}
                className="bg-elzar-red hover:bg-red-600 disabled:bg-gray-600 text-white font-bold py-2 px-6 rounded-lg transition-colors"
              >
                {loading ? 'Processing...' : getActionButtonText()}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default RecipeIngredientReview;
