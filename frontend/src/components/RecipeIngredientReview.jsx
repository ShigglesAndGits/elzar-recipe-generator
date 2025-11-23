import React, { useState, useEffect } from 'react';
import { 
  purchaseItems, 
  consumeItems
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
        create_if_missing: item.confidence === 'new' // Flag for backend to create
      })));
    }
  }, [parsedItems]);

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
        amount: item.quantity,
        unit: item.unit,
        location_id: item.location_id,
        quantity_unit_id: item.quantity_unit_id,
        best_before_date: null,
        action: actionType === 'consume' ? 'consume' : 'purchase',
        create_if_missing: item.create_if_missing && !item.grocy_product_id
      }));

      let result;
      if (actionType === 'consume') {
        result = await consumeItems({ items: transactionItems });
        setResults({ type: 'consume', data: result });
      } else {
        // For shopping list and save, use purchase
        result = await purchaseItems({ items: transactionItems });
        setResults({ type: actionType, data: result });
      }

      if (onComplete) {
        onComplete(result);
      }
    } catch (err) {
      setError(err.response?.data?.detail || `Failed to ${actionType} items.`);
      console.error('Action error:', err);
    } finally {
      setLoading(false);
    }
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

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gray-700 px-6 py-4 border-b border-gray-600">
          <h3 className="text-xl font-bold text-white">{getActionTitle()}</h3>
          <p className="text-sm text-gray-300 mt-1">
            Review and confirm ingredients before proceeding
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
              <table className="min-w-full bg-gray-700 rounded-lg">
                <thead>
                  <tr className="bg-gray-600 text-left text-sm font-semibold text-gray-200">
                    <th className="p-3 rounded-tl-lg">Select</th>
                    <th className="p-3">Ingredient</th>
                    <th className="p-3">Quantity</th>
                    <th className="p-3">Unit</th>
                    <th className="p-3">Grocy Match</th>
                    <th className="p-3">Status</th>
                    <th className="p-3 rounded-tr-lg">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, index) => (
                    <tr key={index} className="border-t border-gray-600 hover:bg-gray-600">
                      <td className="p-3">
                        <input
                          type="checkbox"
                          checked={item.selected}
                          onChange={() => toggleItemSelection(index)}
                          disabled={!item.grocy_product_id}
                          className="form-checkbox text-elzar-red"
                        />
                      </td>
                      <td className="p-3 text-sm">{item.item_name}</td>
                      <td className="p-3 text-sm">{item.quantity}</td>
                      <td className="p-3 text-sm">{item.unit}</td>
                      <td className="p-3 text-sm">
                        {item.grocy_product_name || (
                          <span className="text-yellow-400">No Match</span>
                        )}
                      </td>
                      <td className="p-3 text-sm">
                        <span className={`px-2 py-1 rounded text-xs ${
                          item.confidence === 'high' ? 'bg-green-700 text-green-200' :
                          item.confidence === 'medium' ? 'bg-yellow-700 text-yellow-200' :
                          item.confidence === 'low' ? 'bg-orange-700 text-orange-200' :
                          'bg-red-700 text-red-200'
                        }`}>
                          {item.confidence === 'new' ? 'NEW' : item.confidence.toUpperCase()}
                        </span>
                      </td>
                      <td className="p-3 text-sm">
                        {item.confidence === 'new' && !item.grocy_product_id ? (
                          <label className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={item.create_if_missing}
                              onChange={() => handleToggleCreateIfMissing(index)}
                              className="form-checkbox text-blue-600"
                            />
                            <span className="text-xs">Auto-create</span>
                          </label>
                        ) : (
                          <span className="text-xs text-gray-500">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="mt-4 text-sm text-gray-400">
                <p>💡 <strong>Tip:</strong> Items marked "NEW" will be automatically created in Grocy if "Auto-create" is checked.</p>
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
        <div className="bg-gray-700 px-6 py-4 border-t border-gray-600 flex justify-between">
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
  );
}

export default RecipeIngredientReview;

