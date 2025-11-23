import React, { useState } from 'react';
import { parseInventoryText, purchaseItems, consumeItems } from '../api';

function InventoryManager() {
  const [inputText, setInputText] = useState('');
  const [actionType, setActionType] = useState('purchase');
  const [parsedItems, setParsedItems] = useState([]);
  const [parsing, setParsing] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);

  const handleParse = async () => {
    if (!inputText.trim()) {
      setError('Please enter some text to parse');
      return;
    }

    setParsing(true);
    setError(null);
    setParsedItems([]);
    setResults(null);

    try {
      const items = await parseInventoryText(inputText, actionType);
      
      // Initialize items with default actions
      const itemsWithActions = items.map(item => ({
        ...item,
        action: actionType,
        create_if_missing: item.confidence === 'new',
        editable: true
      }));
      
      setParsedItems(itemsWithActions);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to parse text. Check your backend connection.');
      console.error('Parse error:', err);
    } finally {
      setParsing(false);
    }
  };

  const handleItemChange = (index, field, value) => {
    const updated = [...parsedItems];
    updated[index][field] = value;
    setParsedItems(updated);
  };

  const handleActionChange = (index, action) => {
    const updated = [...parsedItems];
    updated[index].action = action;
    setParsedItems(updated);
  };

  const handleProcessItem = async (index) => {
    const item = parsedItems[index];
    setProcessing(true);
    setError(null);

    try {
      const itemData = {
        product_id: item.matched_product_id,
        product_name: item.item_name,
        quantity: item.quantity,
        unit: item.unit,
        action: item.action,
        create_if_missing: item.create_if_missing && item.confidence === 'new',
        location_id: item.suggested_location_id
      };

      let result;
      if (item.action === 'purchase') {
        result = await purchaseItems([itemData]);
      } else if (item.action === 'consume') {
        result = await consumeItems([itemData]);
      }

      // Mark item as processed
      const updated = [...parsedItems];
      updated[index].processed = true;
      updated[index].result = result;
      setParsedItems(updated);

    } catch (err) {
      setError(`Failed to process item: ${err.response?.data?.detail || err.message}`);
      console.error('Process error:', err);
    } finally {
      setProcessing(false);
    }
  };

  const handleProcessAll = async () => {
    setProcessing(true);
    setError(null);
    setResults(null);

    try {
      // Separate items by action
      const purchaseList = parsedItems
        .filter(item => item.action === 'purchase' && !item.processed)
        .map(item => ({
          product_id: item.matched_product_id,
          product_name: item.item_name,
          quantity: item.quantity,
          unit: item.unit,
          action: 'purchase',
          create_if_missing: item.create_if_missing && item.confidence === 'new',
          location_id: item.suggested_location_id
        }));

      const consumeList = parsedItems
        .filter(item => item.action === 'consume' && !item.processed)
        .map(item => ({
          product_id: item.matched_product_id,
          product_name: item.item_name,
          quantity: item.quantity,
          unit: item.unit,
          action: 'consume',
          create_if_missing: false,
          location_id: item.suggested_location_id
        }));

      const results = {
        purchase: null,
        consume: null
      };

      if (purchaseList.length > 0) {
        results.purchase = await purchaseItems(purchaseList);
      }

      if (consumeList.length > 0) {
        results.consume = await consumeItems(consumeList);
      }

      setResults(results);

      // Mark all items as processed
      const updated = parsedItems.map(item => ({ ...item, processed: true }));
      setParsedItems(updated);

    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to process items');
      console.error('Process all error:', err);
    } finally {
      setProcessing(false);
    }
  };

  const handleClear = () => {
    setInputText('');
    setParsedItems([]);
    setError(null);
    setResults(null);
  };

  const getConfidenceBadge = (confidence) => {
    const colors = {
      high: 'bg-green-600',
      medium: 'bg-yellow-600',
      low: 'bg-orange-600',
      new: 'bg-blue-600'
    };
    return (
      <span className={`${colors[confidence] || 'bg-gray-600'} text-white text-xs px-2 py-1 rounded`}>
        {confidence.toUpperCase()}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
        <h2 className="text-2xl font-bold mb-4 flex items-center">
          <span className="text-3xl mr-2">📦</span>
          Inventory Manager
        </h2>
        <p className="text-gray-400 mb-4">
          Paste receipts, shopping lists, or ingredient lists. The LLM will parse and match items to your Grocy inventory.
        </p>

        {/* Action Type Selection */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">Action Type</label>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => setActionType('purchase')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                actionType === 'purchase'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              📥 Purchase (Add to Stock)
            </button>
            <button
              onClick={() => setActionType('consume')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                actionType === 'consume'
                  ? 'bg-red-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              📤 Consume (Remove from Stock)
            </button>
          </div>
        </div>

        {/* Text Input */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">Paste Text</label>
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Paste your receipt, shopping list, or ingredient list here...&#10;&#10;Example:&#10;1 gallon 2% milk&#10;2 lbs organic bananas&#10;1 dozen eggs&#10;16 oz pasta"
            rows="8"
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 focus:ring-2 focus:ring-elzar-red font-mono text-sm"
          />
        </div>

        {/* Parse Button */}
        <div className="flex space-x-2">
          <button
            onClick={handleParse}
            disabled={parsing || !inputText.trim()}
            className="bg-elzar-orange hover:bg-orange-600 disabled:bg-gray-600 text-white font-semibold py-2 px-6 rounded-lg transition-colors"
          >
            {parsing ? '🔄 Parsing...' : '🧠 Parse with LLM'}
          </button>
          {parsedItems.length > 0 && (
            <button
              onClick={handleClear}
              className="bg-gray-700 hover:bg-gray-600 text-white font-semibold py-2 px-6 rounded-lg transition-colors"
            >
              Clear
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

      {/* Parsed Items Table */}
      {parsedItems.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
          <h3 className="text-xl font-bold mb-4">Parsed Items ({parsedItems.length})</h3>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-2 px-2">Original</th>
                  <th className="text-left py-2 px-2">Item Name</th>
                  <th className="text-left py-2 px-2">Quantity</th>
                  <th className="text-left py-2 px-2">Unit</th>
                  <th className="text-left py-2 px-2">Matched Product</th>
                  <th className="text-left py-2 px-2">Confidence</th>
                  <th className="text-left py-2 px-2">Action</th>
                  <th className="text-left py-2 px-2"></th>
                </tr>
              </thead>
              <tbody>
                {parsedItems.map((item, index) => (
                  <tr key={index} className={`border-b border-gray-700 ${item.processed ? 'opacity-50' : ''}`}>
                    <td className="py-2 px-2 text-gray-400 text-xs">{item.original_text}</td>
                    <td className="py-2 px-2">
                      <input
                        type="text"
                        value={item.item_name}
                        onChange={(e) => handleItemChange(index, 'item_name', e.target.value)}
                        disabled={item.processed}
                        className="bg-gray-700 border border-gray-600 rounded px-2 py-1 w-full text-sm"
                      />
                    </td>
                    <td className="py-2 px-2">
                      <input
                        type="number"
                        value={item.quantity}
                        onChange={(e) => handleItemChange(index, 'quantity', parseFloat(e.target.value))}
                        disabled={item.processed}
                        className="bg-gray-700 border border-gray-600 rounded px-2 py-1 w-20 text-sm"
                        step="0.1"
                      />
                    </td>
                    <td className="py-2 px-2">
                      <input
                        type="text"
                        value={item.unit}
                        onChange={(e) => handleItemChange(index, 'unit', e.target.value)}
                        disabled={item.processed}
                        className="bg-gray-700 border border-gray-600 rounded px-2 py-1 w-16 text-sm"
                      />
                    </td>
                    <td className="py-2 px-2">
                      <span className="text-sm">
                        {item.matched_product_name || 'NEW PRODUCT'}
                      </span>
                    </td>
                    <td className="py-2 px-2">
                      {getConfidenceBadge(item.confidence)}
                    </td>
                    <td className="py-2 px-2">
                      <select
                        value={item.action}
                        onChange={(e) => handleActionChange(index, e.target.value)}
                        disabled={item.processed}
                        className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm"
                      >
                        <option value="purchase">Purchase</option>
                        <option value="consume">Consume</option>
                        <option value="skip">Skip</option>
                      </select>
                    </td>
                    <td className="py-2 px-2">
                      {!item.processed && (
                        <button
                          onClick={() => handleProcessItem(index)}
                          disabled={processing || item.action === 'skip'}
                          className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white text-xs px-3 py-1 rounded transition-colors"
                        >
                          {item.action === 'purchase' ? '📥' : '📤'}
                        </button>
                      )}
                      {item.processed && (
                        <span className="text-green-400 text-xs">✓ Done</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Bulk Actions */}
          <div className="mt-4 flex space-x-2">
            <button
              onClick={handleProcessAll}
              disabled={processing || parsedItems.every(item => item.processed || item.action === 'skip')}
              className="bg-elzar-red hover:bg-red-600 disabled:bg-gray-600 text-white font-semibold py-2 px-6 rounded-lg transition-colors"
            >
              {processing ? '⏳ Processing...' : '🚀 Process All'}
            </button>
          </div>

          {/* Results Summary */}
          {results && (
            <div className="mt-4 bg-gray-700 rounded-lg p-4">
              <h4 className="font-semibold mb-2">Results Summary</h4>
              
              {results.purchase && (
                <div className="mb-2">
                  <p className="text-sm text-green-400">
                    ✓ Purchased {results.purchase.success.length} items
                  </p>
                  {results.purchase.created_products.length > 0 && (
                    <p className="text-sm text-blue-400">
                      + Created {results.purchase.created_products.length} new products
                    </p>
                  )}
                  {results.purchase.failed.length > 0 && (
                    <p className="text-sm text-red-400">
                      ✗ Failed {results.purchase.failed.length} items
                    </p>
                  )}
                </div>
              )}

              {results.consume && (
                <div>
                  <p className="text-sm text-green-400">
                    ✓ Consumed {results.consume.success.length} items
                  </p>
                  {results.consume.failed.length > 0 && (
                    <p className="text-sm text-red-400">
                      ✗ Failed {results.consume.failed.length} items
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default InventoryManager;

