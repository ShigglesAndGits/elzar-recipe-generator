import React from 'react';

function GrocyActionModal({ isOpen, onClose, title, results, actionType }) {
  if (!isOpen || !results) return null;

  const renderConsumeResults = () => (
    <>
      {results.consumed && results.consumed.length > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold text-green-400 mb-2">
            ✓ Consumed {results.consumed.length} ingredients
          </h4>
          <ul className="text-sm text-gray-300 ml-4 space-y-1">
            {results.consumed.map((item, idx) => (
              <li key={idx}>
                • {item.product_name}: {item.quantity} {item.unit}
              </li>
            ))}
          </ul>
        </div>
      )}

      {results.insufficient_stock && results.insufficient_stock.length > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold text-yellow-400 mb-2">
            ⚠ {results.insufficient_stock.length} items had insufficient stock
          </h4>
          <ul className="text-sm text-gray-300 ml-4 space-y-1">
            {results.insufficient_stock.map((item, idx) => (
              <li key={idx}>
                • {item.ingredient}: needed {item.needed} {item.unit}, only had {item.available} {item.unit}
              </li>
            ))}
          </ul>
        </div>
      )}

      {results.skipped && results.skipped.length > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold text-red-400 mb-2">
            ✗ Skipped {results.skipped.length} items
          </h4>
          <ul className="text-sm text-gray-300 ml-4 space-y-1">
            {results.skipped.map((item, idx) => (
              <li key={idx}>
                • {item.ingredient}: {item.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );

  const renderShoppingListResults = () => (
    <>
      {results.added && results.added.length > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold text-green-400 mb-2">
            ✓ Added {results.added.length} items to shopping list
          </h4>
          <ul className="text-sm text-gray-300 ml-4 space-y-1">
            {results.added.map((item, idx) => (
              <li key={idx}>
                • {item.product_name}: {item.quantity} {item.unit}
              </li>
            ))}
          </ul>
        </div>
      )}

      {results.already_in_stock && results.already_in_stock.length > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold text-blue-400 mb-2">
            ℹ {results.already_in_stock.length} items already in stock
          </h4>
          <ul className="text-sm text-gray-300 ml-4 space-y-1">
            {results.already_in_stock.map((item, idx) => (
              <li key={idx}>
                • {item.product_name}: {item.stock_amount} {item.unit} available
              </li>
            ))}
          </ul>
        </div>
      )}

      {results.skipped && results.skipped.length > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold text-red-400 mb-2">
            ✗ Skipped {results.skipped.length} items
          </h4>
          <ul className="text-sm text-gray-300 ml-4 space-y-1">
            {results.skipped.map((item, idx) => (
              <li key={idx}>
                • {item.ingredient}: {item.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );

  const renderSaveRecipeResults = () => (
    <>
      <div className="mb-4">
        <h4 className="font-semibold text-green-400 mb-2">
          ✓ Recipe saved to Grocy!
        </h4>
        <div className="text-sm text-gray-300 ml-4 space-y-1">
          <p><span className="font-semibold">Recipe:</span> {results.recipe_name}</p>
          <p><span className="font-semibold">Servings:</span> {results.servings}</p>
          <p><span className="font-semibold">Grocy Recipe ID:</span> {results.grocy_recipe_id}</p>
        </div>
      </div>

      {results.ingredients_added && results.ingredients_added.length > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold text-green-400 mb-2">
            ✓ Added {results.ingredients_added.length} ingredients
          </h4>
          <ul className="text-sm text-gray-300 ml-4 space-y-1">
            {results.ingredients_added.map((item, idx) => (
              <li key={idx}>
                • {item.product_name}: {item.quantity} {item.unit}
              </li>
            ))}
          </ul>
        </div>
      )}

      {results.ingredients_skipped && results.ingredients_skipped.length > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold text-red-400 mb-2">
            ✗ Skipped {results.ingredients_skipped.length} ingredients
          </h4>
          <ul className="text-sm text-gray-300 ml-4 space-y-1">
            {results.ingredients_skipped.map((item, idx) => (
              <li key={idx}>
                • {item.ingredient}: {item.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gray-700 px-6 py-4 border-b border-gray-600">
          <h3 className="text-xl font-bold text-white">{title}</h3>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto flex-1">
          {actionType === 'consume' && renderConsumeResults()}
          {actionType === 'shopping' && renderShoppingListResults()}
          {actionType === 'save' && renderSaveRecipeResults()}
        </div>

        {/* Footer */}
        <div className="bg-gray-700 px-6 py-4 border-t border-gray-600 flex justify-end">
          <button
            onClick={onClose}
            className="bg-elzar-red hover:bg-red-600 text-white font-bold py-2 px-6 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default GrocyActionModal;

