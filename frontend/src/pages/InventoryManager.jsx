import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useServiceStatus } from '../contexts/ServiceStatusContext';
import { parseInventoryText, purchaseItems, consumeItems, scanPantryImages, getFreezerStock, consumeFreezerItem } from '../api';

function InventoryManager() {
  const { grocyConfigured } = useServiceStatus();

  // All hooks must be declared before any early returns (React rules of hooks)
  const [inputText, setInputText] = useState('');
  const [actionType, setActionType] = useState('purchase');
  const [inputMode, setInputMode] = useState('text'); // 'text' or 'scan'
  const [parsedItems, setParsedItems] = useState([]);
  const [parsing, setParsing] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [previewUrls, setPreviewUrls] = useState([]);
  const fileInputRef = useRef(null);

  // Freezer state
  const [freezerItems, setFreezerItems] = useState([]);
  const [freezerLocations, setFreezerLocations] = useState([]);
  const [freezerLoading, setFreezerLoading] = useState(false);
  const [freezerError, setFreezerError] = useState(null);
  const [freezerSearch, setFreezerSearch] = useState('');
  const [consumingId, setConsumingId] = useState(null);

  if (!grocyConfigured) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-gray-800 rounded-lg p-8 shadow-lg text-center">
          <span className="text-6xl mb-4 block">📦</span>
          <h2 className="text-2xl font-bold mb-3">Inventory Manager</h2>
          <p className="text-gray-400 mb-6">
            The Inventory Manager requires a Grocy connection to manage your pantry, fridge, and freezer stock.
          </p>
          <Link
            to="/settings"
            className="inline-block bg-elzar-red hover:bg-red-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
          >
            Configure Grocy in Settings
          </Link>
        </div>
      </div>
    );
  }

  const loadFreezerStock = async () => {
    setFreezerLoading(true);
    setFreezerError(null);
    try {
      const data = await getFreezerStock();
      setFreezerItems(data.items || []);
      setFreezerLocations(data.freezer_locations || []);
    } catch (err) {
      // Silently handle if Grocy isn't configured - the section just won't show
      if (err.response?.status !== 503) {
        setFreezerError(err.response?.data?.detail || 'Failed to load freezer stock');
      }
    } finally {
      setFreezerLoading(false);
    }
  };

  // Load freezer stock on mount (only when Grocy is configured)
  useEffect(() => {
    if (grocyConfigured) {
      loadFreezerStock();
    }
  }, [grocyConfigured]);

  const handleConsumeFreezer = async (item, amount) => {
    setConsumingId(item.product_id);
    try {
      await consumeFreezerItem([{
        product_id: item.product_id,
        product_name: item.product_name,
        amount: amount,
        unit: item.unit,
        action: 'consume',
        location_id: item.location_id,
      }]);
      // Reload to get updated quantities
      await loadFreezerStock();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to consume from freezer');
    } finally {
      setConsumingId(null);
    }
  };

  const filteredFreezerItems = freezerItems.filter(item =>
    item.product_name.toLowerCase().includes(freezerSearch.toLowerCase())
  );

  const getDaysAgo = (dateStr) => {
    if (!dateStr) return null;
    const date = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    return diff;
  };

  const getFreezerAgeBadge = (dateStr) => {
    const days = getDaysAgo(dateStr);
    if (days === null) return null;
    if (days <= 30) return { label: `${days}d ago`, color: 'text-green-400' };
    if (days <= 90) return { label: `${Math.floor(days / 7)}w ago`, color: 'text-yellow-400' };
    return { label: `${Math.floor(days / 30)}mo ago`, color: 'text-orange-400' };
  };

  const getExpiryBadge = (dateStr) => {
    if (!dateStr) return null;
    const date = new Date(dateStr);
    const now = new Date();
    const daysUntil = Math.floor((date - now) / (1000 * 60 * 60 * 24));
    if (daysUntil < 0) return { label: 'Expired', color: 'bg-red-600' };
    if (daysUntil <= 7) return { label: `${daysUntil}d left`, color: 'bg-orange-600' };
    if (daysUntil <= 30) return { label: `${Math.floor(daysUntil / 7)}w left`, color: 'bg-yellow-600' };
    return { label: `${Math.floor(daysUntil / 30)}mo left`, color: 'bg-green-700' };
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    // Validate file types
    const validFiles = files.filter(file =>
      ['image/jpeg', 'image/png', 'image/webp', 'image/jpg'].includes(file.type)
    );

    if (validFiles.length !== files.length) {
      setError('Some files were skipped. Only JPEG, PNG, and WebP images are allowed.');
    }

    // Create preview URLs
    const urls = validFiles.map(file => URL.createObjectURL(file));

    setSelectedFiles(prev => [...prev, ...validFiles]);
    setPreviewUrls(prev => [...prev, ...urls]);
  };

  const handleRemoveFile = (index) => {
    URL.revokeObjectURL(previewUrls[index]);
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
    setPreviewUrls(prev => prev.filter((_, i) => i !== index));
  };

  const handleClearFiles = () => {
    previewUrls.forEach(url => URL.revokeObjectURL(url));
    setSelectedFiles([]);
    setPreviewUrls([]);
  };

  const handleScanImages = async () => {
    if (selectedFiles.length === 0) {
      setError('Please select at least one image to scan');
      return;
    }

    setParsing(true);
    setError(null);
    setParsedItems([]);
    setResults(null);

    try {
      const items = await scanPantryImages(selectedFiles);

      // Initialize items with default actions (always purchase for scanned items)
      const itemsWithActions = items.map(item => {
        const hasMatch = item.grocy_product_id && item.grocy_product_id !== null && item.grocy_product_id > 0;

        return {
          ...item,
          action: 'purchase',
          create_if_missing: !hasMatch,
          editable: true,
          processed: false
        };
      });

      setParsedItems(itemsWithActions);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to scan images. Make sure vision model is configured in Settings.');
      console.error('Scan error:', err);
    } finally {
      setParsing(false);
    }
  };

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
      const itemsWithActions = items.map(item => {
        // Check if product is matched (has a valid product ID)
        const hasMatch = item.grocy_product_id && item.grocy_product_id !== null && item.grocy_product_id > 0;

        return {
          ...item,
          action: actionType,
          // Auto-create if no product match found
          create_if_missing: !hasMatch,
          editable: true,
          processed: false
        };
      });

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
        product_id: item.grocy_product_id,  // Use grocy_product_id
        product_name: item.item_name,
        amount: item.quantity,  // Backend expects 'amount', not 'quantity'
        unit: item.unit,
        action: item.action,
        create_if_missing: item.action === 'purchase' ? item.create_if_missing : false,  // Only allow create for purchase
        location_id: item.location_id  // Use location_id
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
          product_id: item.grocy_product_id,  // Use grocy_product_id
          product_name: item.item_name,
          amount: item.quantity,  // Backend expects 'amount', not 'quantity'
          unit: item.unit,
          action: 'purchase',
          create_if_missing: item.create_if_missing,  // Use the checkbox value directly
          location_id: item.location_id  // Use location_id
        }));

      const consumeList = parsedItems
        .filter(item => item.action === 'consume' && !item.processed)
        .map(item => ({
          product_id: item.grocy_product_id,  // Use grocy_product_id, not matched_product_id
          product_name: item.item_name,
          amount: item.quantity,  // Backend expects 'amount', not 'quantity'
          unit: item.unit,
          action: 'consume',
          create_if_missing: false,  // Cannot create products when consuming
          location_id: item.location_id  // Use location_id, not suggested_location_id
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
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to process items';
      setError(errorMessage);
      console.error('Process all error:', err);
      // Show alert as well for immediate visibility
      alert(`Error processing items: ${errorMessage}`);
    } finally {
      setProcessing(false);
    }
  };

  const handleClear = () => {
    setInputText('');
    setParsedItems([]);
    setError(null);
    setResults(null);
    handleClearFiles();
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
          Add items to your Grocy inventory by pasting text or scanning photos of your pantry/fridge.
        </p>

        {/* Input Mode Toggle */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">Input Method</label>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => setInputMode('text')}
              className={`px-4 py-3 rounded-lg transition-colors flex items-center justify-center ${
                inputMode === 'text'
                  ? 'bg-elzar-orange text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              <span className="mr-2">📝</span> Paste Text
            </button>
            <button
              onClick={() => setInputMode('scan')}
              className={`px-4 py-3 rounded-lg transition-colors flex items-center justify-center ${
                inputMode === 'scan'
                  ? 'bg-elzar-orange text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              <span className="mr-2">📷</span> Scan Photos
            </button>
          </div>
        </div>

        {/* Text Input Mode */}
        {inputMode === 'text' && (
          <>
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
          </>
        )}

        {/* Scan Photos Mode */}
        {inputMode === 'scan' && (
          <>
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Upload Photos</label>
              <p className="text-xs text-gray-400 mb-3">
                Take photos of your pantry, fridge, or shelves. The AI will identify food items and match them to your Grocy products.
              </p>

              {/* Hidden file input */}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                accept="image/jpeg,image/png,image/webp"
                multiple
                className="hidden"
              />

              {/* Upload area */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center cursor-pointer hover:border-elzar-orange hover:bg-gray-700/50 transition-colors"
              >
                <div className="text-4xl mb-2">📷</div>
                <p className="text-gray-300 font-medium">Click to select photos</p>
                <p className="text-gray-500 text-sm mt-1">or drag and drop</p>
                <p className="text-gray-500 text-xs mt-2">JPEG, PNG, WebP (max 20MB each)</p>
              </div>

              {/* Image previews */}
              {previewUrls.length > 0 && (
                <div className="mt-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium">{selectedFiles.length} photo(s) selected</span>
                    <button
                      onClick={handleClearFiles}
                      className="text-xs text-gray-400 hover:text-white"
                    >
                      Clear all
                    </button>
                  </div>
                  <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2">
                    {previewUrls.map((url, index) => (
                      <div key={index} className="relative group">
                        <img
                          src={url}
                          alt={`Preview ${index + 1}`}
                          className="w-full h-24 object-cover rounded-lg"
                        />
                        <button
                          onClick={() => handleRemoveFile(index)}
                          className="absolute top-1 right-1 bg-red-600 text-white rounded-full w-5 h-5 text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                    {/* Add more button */}
                    <div
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full h-24 border-2 border-dashed border-gray-600 rounded-lg flex items-center justify-center cursor-pointer hover:border-elzar-orange hover:bg-gray-700/50 transition-colors"
                    >
                      <span className="text-2xl text-gray-500">+</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Scan Button */}
            <div className="flex space-x-2">
              <button
                onClick={handleScanImages}
                disabled={parsing || selectedFiles.length === 0}
                className="bg-elzar-orange hover:bg-orange-600 disabled:bg-gray-600 text-white font-semibold py-2 px-6 rounded-lg transition-colors"
              >
                {parsing ? '🔄 Scanning...' : '📷 Scan with Vision AI'}
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

            {/* Vision model note */}
            <div className="mt-4 bg-blue-900 border border-blue-700 rounded-lg p-3 text-blue-200">
              <p className="text-xs">
                💡 <strong>Tip:</strong> Make sure a vision-capable model is configured in Settings.
                GPT-4o, Gemini, and Claude all support image analysis.
              </p>
            </div>
          </>
        )}

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
                  <th className="text-left py-2 px-2">Auto-create</th>
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
                    <td className="py-2 px-2 text-center">
                      <input
                        type="checkbox"
                        checked={!!item.create_if_missing}
                        onChange={(e) => handleItemChange(index, 'create_if_missing', e.target.checked)}
                        disabled={item.processed}
                        className="form-checkbox text-blue-600 w-4 h-4 cursor-pointer disabled:cursor-not-allowed"
                        title={item.grocy_product_id ? "Product already matched" : "Create product if it doesn't exist"}
                      />
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
                    <div className="mt-2">
                      <p className="text-sm text-red-400 font-semibold">
                        ✗ Failed {results.purchase.failed.length} items:
                      </p>
                      <ul className="text-xs text-red-300 ml-4 mt-1">
                        {results.purchase.failed.map((item, idx) => (
                          <li key={idx}>• {item.product_name}: {item.reason}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {results.consume && (
                <div>
                  <p className="text-sm text-green-400">
                    ✓ Consumed {results.consume.success.length} items
                  </p>
                  {results.consume.failed.length > 0 && (
                    <div className="mt-2">
                      <p className="text-sm text-red-400 font-semibold">
                        ✗ Failed {results.consume.failed.length} items:
                      </p>
                      <ul className="text-xs text-red-300 ml-4 mt-1">
                        {results.consume.failed.map((item, idx) => (
                          <li key={idx}>• {item.product_name}: {item.reason}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Freezer Dashboard */}
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold flex items-center">
            <span className="text-3xl mr-2">🧊</span>
            Freezer
          </h2>
          <button
            onClick={loadFreezerStock}
            disabled={freezerLoading}
            className="bg-gray-700 hover:bg-gray-600 text-white text-sm px-3 py-1.5 rounded-lg transition-colors"
          >
            {freezerLoading ? '...' : '↻ Refresh'}
          </button>
        </div>

        {freezerError && (
          <div className="bg-red-900 border border-red-700 rounded-lg p-3 text-red-200 text-sm mb-4">
            {freezerError}
          </div>
        )}

        {freezerLocations.length === 0 && !freezerLoading && !freezerError && (
          <div className="text-center py-8 text-gray-400">
            <p className="text-4xl mb-3">🧊</p>
            <p>No freezer location found in Grocy.</p>
            <p className="text-sm mt-1">Go to Settings → Setup Storage Locations to create one.</p>
          </div>
        )}

        {freezerLocations.length > 0 && (
          <>
            {/* Search */}
            {freezerItems.length > 0 && (
              <input
                type="text"
                value={freezerSearch}
                onChange={(e) => setFreezerSearch(e.target.value)}
                placeholder="Search freezer..."
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm mb-4 focus:ring-2 focus:ring-cyan-500"
              />
            )}

            {/* Summary */}
            {freezerItems.length > 0 && (
              <div className="flex gap-4 mb-4 text-sm text-gray-400">
                <span>{freezerItems.length} item{freezerItems.length !== 1 ? 's' : ''}</span>
                <span>•</span>
                <span>{freezerLocations.map(l => l.name).join(', ')}</span>
              </div>
            )}

            {/* Empty state */}
            {!freezerLoading && freezerItems.length === 0 && (
              <div className="text-center py-8 text-gray-400">
                <p className="text-4xl mb-3">❄️</p>
                <p>Freezer is empty</p>
                <p className="text-sm mt-1">Purchase items to a freezer location in Grocy to see them here</p>
              </div>
            )}

            {/* Loading */}
            {freezerLoading && (
              <div className="text-center py-8 text-gray-400">Loading freezer stock...</div>
            )}

            {/* Freezer Items Grid */}
            {!freezerLoading && filteredFreezerItems.length > 0 && (
              <div className="space-y-2">
                {filteredFreezerItems.map((item) => {
                  const ageBadge = getFreezerAgeBadge(item.earliest_purchased);
                  const expiryBadge = getExpiryBadge(item.best_before_date);

                  return (
                    <div
                      key={item.product_id}
                      className="bg-gray-700 rounded-lg p-4 flex items-center justify-between hover:bg-gray-650 transition-colors"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold">{item.product_name}</h3>
                          {expiryBadge && (
                            <span className={`${expiryBadge.color} text-white text-xs px-2 py-0.5 rounded`}>
                              {expiryBadge.label}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-sm text-gray-400">
                          <span className="text-white font-medium">
                            {item.amount} {item.unit}{item.amount !== 1 ? 's' : ''}
                          </span>
                          <span className="text-gray-500">•</span>
                          <span>{item.location_name}</span>
                          {ageBadge && (
                            <>
                              <span className="text-gray-500">•</span>
                              <span className={ageBadge.color}>Frozen {ageBadge.label}</span>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Quick consume buttons */}
                      <div className="flex items-center gap-2 ml-4">
                        <button
                          onClick={() => handleConsumeFreezer(item, 1)}
                          disabled={consumingId === item.product_id || item.amount < 1}
                          className="bg-cyan-700 hover:bg-cyan-600 disabled:bg-gray-600 text-white text-xs px-3 py-1.5 rounded transition-colors"
                          title="Use 1 portion"
                        >
                          {consumingId === item.product_id ? '...' : '-1'}
                        </button>
                        {item.amount > 1 && (
                          <button
                            onClick={() => handleConsumeFreezer(item, item.amount)}
                            disabled={consumingId === item.product_id}
                            className="bg-orange-700 hover:bg-orange-600 disabled:bg-gray-600 text-white text-xs px-3 py-1.5 rounded transition-colors"
                            title="Use all"
                          >
                            {consumingId === item.product_id ? '...' : 'All'}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* No search results */}
            {!freezerLoading && freezerItems.length > 0 && filteredFreezerItems.length === 0 && (
              <div className="text-center py-6 text-gray-400">
                No items match "{freezerSearch}"
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default InventoryManager;

