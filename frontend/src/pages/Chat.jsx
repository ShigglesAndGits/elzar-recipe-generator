import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { useServiceStatus } from '../contexts/ServiceStatusContext';
import {
  sendChatMessage,
  getChatSessions,
  getChatSession,
  renameChatSession,
  deleteChatSession,
  getAllProfiles,
} from '../api';

const CUISINES = [
  'No Preference', 'American', 'Asian (General)', 'BBQ / Grilling', 'British',
  'Cajun / Creole', 'Caribbean', 'Chinese', 'Ethiopian', 'French', 'German',
  'Greek', 'Indian', 'Italian', 'Japanese', 'Korean', 'Mediterranean',
  'Mexican', 'Middle Eastern', 'Moroccan', 'Soul Food', 'Southern', 'Spanish',
  'Thai', 'Vietnamese',
];

const KITCHEN_EQUIPMENT = [
  'Oven', 'Stovetop', 'Microwave', 'Air Fryer', 'Instant Pot', 'Slow Cooker',
  'Electric Kettle', 'Grill', 'Toaster Oven', 'Sous Vide', 'Blender', 'Food Processor',
];

// Cookie helpers (shared pattern with Generator)
const saveToCookie = (key, value) => {
  try {
    document.cookie = `elzar_chat_${key}=${encodeURIComponent(JSON.stringify(value))}; path=/; max-age=31536000`;
  } catch (e) { console.error('Failed to save cookie:', e); }
};

const loadFromCookie = (key, defaultValue) => {
  try {
    const name = `elzar_chat_${key}=`;
    const decodedCookie = decodeURIComponent(document.cookie);
    const cookies = decodedCookie.split(';');
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.indexOf(name) === 0) {
        return JSON.parse(cookie.substring(name.length));
      }
    }
  } catch (e) { console.error('Failed to load cookie:', e); }
  return defaultValue;
};


function Chat() {
  const { grocyConfigured } = useServiceStatus();
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Session state
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sessionSidebarOpen, setSessionSidebarOpen] = useState(false);

  // Rename state
  const [renamingSessionId, setRenamingSessionId] = useState(null);
  const [renameValue, setRenameValue] = useState('');

  // Message input
  const [inputMessage, setInputMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  // Collapsible parameter controls
  const [controlsOpen, setControlsOpen] = useState(false);
  const [cuisine, setCuisine] = useState(() => loadFromCookie('cuisine', 'No Preference'));
  const [effortLevel, setEffortLevel] = useState(() => loadFromCookie('effortLevel', 'Medium'));
  const [servings, setServings] = useState(() => loadFromCookie('servings', '3-4'));
  const [caloriesPerServing, setCaloriesPerServing] = useState(() => loadFromCookie('caloriesPerServing', ''));
  const [budgetLevel, setBudgetLevel] = useState(() => loadFromCookie('budgetLevel', 'No Preference'));
  const [availableEquipment, setAvailableEquipment] = useState(() => loadFromCookie('availableEquipment', KITCHEN_EQUIPMENT));
  const [equipmentExpanded, setEquipmentExpanded] = useState(false);
  const [elzarVoice, setElzarVoice] = useState(() => loadFromCookie('elzarVoice', false));
  const [useInventory, setUseInventory] = useState(() => loadFromCookie('useInventory', true));
  const [prioritizeExpiring, setPrioritizeExpiring] = useState(() => loadFromCookie('prioritizeExpiring', false));

  // Profiles
  const [profiles, setProfiles] = useState([]);
  const [activeProfiles, setActiveProfiles] = useState(() => loadFromCookie('activeProfiles', []));

  // Persist controls to cookies
  useEffect(() => { saveToCookie('cuisine', cuisine); }, [cuisine]);
  useEffect(() => { saveToCookie('effortLevel', effortLevel); }, [effortLevel]);
  useEffect(() => { saveToCookie('servings', servings); }, [servings]);
  useEffect(() => { saveToCookie('caloriesPerServing', caloriesPerServing); }, [caloriesPerServing]);
  useEffect(() => { saveToCookie('budgetLevel', budgetLevel); }, [budgetLevel]);
  useEffect(() => { saveToCookie('availableEquipment', availableEquipment); }, [availableEquipment]);
  useEffect(() => { saveToCookie('elzarVoice', elzarVoice); }, [elzarVoice]);
  useEffect(() => { saveToCookie('useInventory', useInventory); }, [useInventory]);
  useEffect(() => { saveToCookie('prioritizeExpiring', prioritizeExpiring); }, [prioritizeExpiring]);
  useEffect(() => { saveToCookie('activeProfiles', activeProfiles); }, [activeProfiles]);

  // Load sessions + profiles on mount
  useEffect(() => {
    loadSessions();
    loadProfiles();
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadSessions = async () => {
    setSessionsLoading(true);
    try {
      const data = await getChatSessions();
      setSessions(data);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setSessionsLoading(false);
    }
  };

  const loadProfiles = async () => {
    try {
      const data = await getAllProfiles();
      setProfiles(data);
    } catch (err) {
      console.error('Failed to load profiles:', err);
    }
  };

  const loadSession = async (sessionId) => {
    try {
      const data = await getChatSession(sessionId);
      setActiveSessionId(sessionId);
      // Filter to only user/assistant messages for display
      const displayMessages = data.messages.filter(
        m => m.role === 'user' || (m.role === 'assistant' && m.content)
      );
      setMessages(displayMessages);
      setSessionSidebarOpen(false);
    } catch (err) {
      console.error('Failed to load session:', err);
      setError('Failed to load chat session');
    }
  };

  const startNewChat = () => {
    setActiveSessionId(null);
    setMessages([]);
    setError(null);
    setSessionSidebarOpen(false);
    inputRef.current?.focus();
  };

  const handleSend = async () => {
    if (!inputMessage.trim() || sending) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setError(null);
    setSending(true);

    // Optimistically add user message to display
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

    try {
      const params = {
        session_id: activeSessionId,
        message: userMessage,
        cuisine: cuisine !== 'No Preference' ? cuisine : null,
        effort_level: effortLevel,
        servings,
        calories_per_serving: caloriesPerServing ? parseInt(caloriesPerServing) : null,
        budget_level: budgetLevel !== 'No Preference' ? budgetLevel : null,
        available_equipment: availableEquipment,
        active_profiles: activeProfiles,
        elzar_voice: elzarVoice,
        use_inventory: useInventory,
        prioritize_expiring: prioritizeExpiring,
      };

      const response = await sendChatMessage(params);

      // Update session ID (might be newly created)
      setActiveSessionId(response.session_id);

      // Add assistant response
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: response.response,
          tool_results: response.tool_results,
        },
      ]);

      // Refresh session list (new session or updated timestamp)
      loadSessions();
    } catch (err) {
      console.error('Chat send error:', err);
      const errorMsg = err.response?.data?.detail || 'Failed to send message. Check your backend connection.';
      setError(errorMsg);
      // Remove optimistic user message on error
      setMessages(prev => prev.slice(0, -1));
      setInputMessage(userMessage); // Restore message for retry
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleDeleteSession = async (sessionId, e) => {
    e.stopPropagation();
    if (!confirm('Delete this chat session?')) return;
    try {
      await deleteChatSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        startNewChat();
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const handleStartRename = (session, e) => {
    e.stopPropagation();
    setRenamingSessionId(session.id);
    setRenameValue(session.name);
  };

  const handleRename = async (sessionId) => {
    if (!renameValue.trim()) {
      setRenamingSessionId(null);
      return;
    }
    try {
      await renameChatSession(sessionId, renameValue.trim());
      setSessions(prev => prev.map(s =>
        s.id === sessionId ? { ...s, name: renameValue.trim() } : s
      ));
    } catch (err) {
      console.error('Failed to rename session:', err);
    }
    setRenamingSessionId(null);
  };

  const toggleProfile = (profileName) => {
    setActiveProfiles(prev =>
      prev.includes(profileName)
        ? prev.filter(n => n !== profileName)
        : [...prev, profileName]
    );
  };

  const toggleEquipment = (equipment) => {
    setAvailableEquipment(prev =>
      prev.includes(equipment)
        ? prev.filter(e => e !== equipment)
        : [...prev, equipment]
    );
  };

  // Get active session name
  const activeSession = sessions.find(s => s.id === activeSessionId);

  return (
    <div className="flex flex-col h-[calc(100vh-5rem)]">
      {/* Top bar: session name + controls toggle */}
      <div className="flex items-center gap-2 mb-2">
        {/* Session sidebar toggle */}
        <button
          onClick={() => setSessionSidebarOpen(!sessionSidebarOpen)}
          className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white transition-colors"
          title="Chat sessions"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
        </button>

        {/* New chat button */}
        <button
          onClick={startNewChat}
          className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white transition-colors"
          title="New chat"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </button>

        {/* Session name */}
        <h2 className="text-lg font-semibold text-white truncate flex-1">
          {activeSession ? activeSession.name : 'New Chat'}
        </h2>

        {/* Spice Weasel toggle (compact) */}
        <button
          onClick={() => setElzarVoice(!elzarVoice)}
          className={`p-2 rounded-lg transition-colors ${
            elzarVoice
              ? 'bg-gradient-to-br from-purple-600 to-orange-500 text-white'
              : 'bg-gray-800 text-gray-500 hover:bg-gray-700'
          }`}
          title={elzarVoice ? 'Spice Weasel: ON' : 'Spice Weasel: OFF'}
        >
          <img
            src="/spice-weasel.webp"
            alt="Spice Weasel"
            className={`h-5 w-5 object-contain ${elzarVoice ? '' : 'opacity-40 grayscale'}`}
          />
        </button>

        {/* Controls toggle */}
        <button
          onClick={() => setControlsOpen(!controlsOpen)}
          className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
            controlsOpen
              ? 'bg-elzar-red text-white'
              : 'bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white'
          }`}
        >
          {controlsOpen ? 'Hide Options' : 'Options'}
        </button>
      </div>

      {/* Collapsible Parameter Controls */}
      {controlsOpen && (
        <div className="bg-gray-800 rounded-lg p-4 mb-2 border border-gray-700">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Cuisine */}
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Cuisine</label>
              <select
                value={cuisine}
                onChange={(e) => setCuisine(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-elzar-red"
              >
                {CUISINES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            {/* Effort Level */}
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Effort</label>
              <div className="flex gap-1">
                {['Low', 'Medium', 'High'].map(level => (
                  <button
                    key={level}
                    onClick={() => setEffortLevel(level)}
                    className={`flex-1 px-2 py-1.5 rounded text-xs font-medium transition-colors ${
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
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Servings</label>
              <div className="flex gap-1">
                {['1-2', '3-4', '5-6', '7+'].map(s => (
                  <button
                    key={s}
                    onClick={() => setServings(s)}
                    className={`flex-1 px-1 py-1.5 rounded text-xs font-medium transition-colors ${
                      servings === s
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            {/* Calories */}
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Cal/serving</label>
              <input
                type="number"
                value={caloriesPerServing}
                onChange={(e) => setCaloriesPerServing(e.target.value)}
                placeholder="Any"
                className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1.5 text-sm focus:ring-1 focus:ring-elzar-red"
              />
            </div>

            {/* Budget */}
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Budget</label>
              <div className="flex gap-1">
                {['No Preference', 'Budget', 'Mid', 'Premium'].map(level => (
                  <button
                    key={level}
                    onClick={() => setBudgetLevel(level)}
                    className={`flex-1 px-1 py-1.5 rounded text-xs font-medium transition-colors ${
                      budgetLevel === level
                        ? 'bg-green-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {level === 'No Preference' ? 'Any' : level}
                  </button>
                ))}
              </div>
            </div>

            {/* Profiles */}
            {profiles.length > 0 && (
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Profiles</label>
                <div className="flex flex-wrap gap-1">
                  {profiles.map(profile => (
                    <button
                      key={profile.id}
                      onClick={() => toggleProfile(profile.name)}
                      className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                        activeProfiles.includes(profile.name)
                          ? 'bg-elzar-red text-white'
                          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }`}
                    >
                      {profile.name}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Toggles */}
            <div className="space-y-1">
              {grocyConfigured && (
                <>
                  <label className="flex items-center gap-1.5 text-xs cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useInventory}
                      onChange={(e) => setUseInventory(e.target.checked)}
                      className="w-3.5 h-3.5 rounded"
                    />
                    <span className="text-gray-300">Use inventory</span>
                  </label>
                  <label className="flex items-center gap-1.5 text-xs cursor-pointer">
                    <input
                      type="checkbox"
                      checked={prioritizeExpiring}
                      onChange={(e) => setPrioritizeExpiring(e.target.checked)}
                      className="w-3.5 h-3.5 rounded"
                    />
                    <span className="text-gray-300">Prioritize expiring</span>
                  </label>
                </>
              )}
            </div>

            {/* Equipment */}
            <div>
              <button
                onClick={() => setEquipmentExpanded(!equipmentExpanded)}
                className="flex items-center gap-1 text-xs font-medium text-gray-400 hover:text-white transition-colors"
              >
                <span>Equipment ({availableEquipment.length}/{KITCHEN_EQUIPMENT.length})</span>
                <span>{equipmentExpanded ? '▼' : '▶'}</span>
              </button>
              {equipmentExpanded && (
                <div className="mt-1 grid grid-cols-2 gap-0.5">
                  {KITCHEN_EQUIPMENT.map(eq => (
                    <label key={eq} className="flex items-center gap-1 text-xs cursor-pointer hover:bg-gray-700 p-1 rounded">
                      <input
                        type="checkbox"
                        checked={availableEquipment.includes(eq)}
                        onChange={() => toggleEquipment(eq)}
                        className="w-3 h-3"
                      />
                      <span className="text-gray-300">{eq}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Main chat area */}
      <div className="flex flex-1 min-h-0 gap-2">
        {/* Session Sidebar */}
        {sessionSidebarOpen && (
          <div className="w-64 flex-shrink-0 bg-gray-800 rounded-lg border border-gray-700 flex flex-col">
            <div className="p-3 border-b border-gray-700 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-300">Chat Sessions</h3>
              <button
                onClick={startNewChat}
                className="text-xs px-2 py-1 rounded bg-elzar-red hover:bg-red-600 text-white transition-colors"
              >
                + New
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {sessionsLoading ? (
                <p className="text-xs text-gray-500 text-center py-4">Loading...</p>
              ) : sessions.length === 0 ? (
                <p className="text-xs text-gray-500 text-center py-4">No sessions yet</p>
              ) : (
                sessions.map(session => (
                  <div
                    key={session.id}
                    onClick={() => loadSession(session.id)}
                    className={`group p-2 rounded cursor-pointer transition-colors ${
                      activeSessionId === session.id
                        ? 'bg-gray-700 text-white'
                        : 'text-gray-400 hover:bg-gray-700/50 hover:text-gray-200'
                    }`}
                  >
                    {renamingSessionId === session.id ? (
                      <input
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onBlur={() => handleRename(session.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleRename(session.id);
                          if (e.key === 'Escape') setRenamingSessionId(null);
                        }}
                        autoFocus
                        className="w-full bg-gray-600 border border-gray-500 rounded px-1.5 py-0.5 text-xs text-white"
                        onClick={(e) => e.stopPropagation()}
                      />
                    ) : (
                      <>
                        <p className="text-xs font-medium truncate">{session.name}</p>
                        <p className="text-[10px] text-gray-500 mt-0.5">
                          {new Date(session.updated_at).toLocaleDateString()}
                        </p>
                        {/* Action buttons */}
                        <div className="hidden group-hover:flex gap-1 mt-1">
                          <button
                            onClick={(e) => handleStartRename(session, e)}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-gray-600 hover:bg-gray-500 text-gray-300"
                          >
                            Rename
                          </button>
                          <button
                            onClick={(e) => handleDeleteSession(session.id, e)}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-red-900/50 hover:bg-red-800 text-red-400"
                          >
                            Delete
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Messages area */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto rounded-lg bg-gray-800 border border-gray-700 p-4 space-y-4">
            {messages.length === 0 && !sending && (
              <div className="flex flex-col items-center justify-center h-full text-gray-500">
                <img src="/elzar.png" alt="Elzar" className="h-20 w-20 object-contain mb-4 opacity-30" />
                <p className="text-lg font-medium">What are we cooking?</p>
                <p className="text-sm mt-1 text-center max-w-md">
                  Ask me to plan meals, create recipes, check your inventory, manage your ideas list, or just chat about food.
                </p>
              </div>
            )}

            {messages.map((msg, idx) => (
              <MessageBubble key={idx} message={msg} />
            ))}

            {sending && (
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-elzar-red to-orange-500 flex items-center justify-center">
                  <img src="/elzar.png" alt="Elzar" className="h-5 w-5 object-contain animate-pulse" />
                </div>
                <div className="bg-gray-700 rounded-lg px-4 py-3 text-gray-300">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-sm text-gray-400">Thinking...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Error display */}
          {error && (
            <div className="mt-2 bg-red-900/50 border border-red-700 rounded-lg px-4 py-2 text-sm text-red-300 flex items-center justify-between">
              <span>{error}</span>
              <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200 ml-2">
                &times;
              </button>
            </div>
          )}

          {/* Input area */}
          <div className="mt-2 flex gap-2">
            <textarea
              ref={inputRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={elzarVoice ? "BAM! What are we kicking up a notch?" : "Ask about recipes, meal planning, inventory..."}
              rows="2"
              disabled={sending}
              className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 focus:ring-2 focus:ring-elzar-red focus:border-transparent resize-none disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={sending || !inputMessage.trim()}
              className="px-6 bg-elzar-red hover:bg-red-600 disabled:bg-gray-700 disabled:text-gray-500 text-white font-bold rounded-lg transition-colors flex items-center gap-2"
            >
              {sending ? (
                <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>
          <p className="text-xs text-gray-600 mt-1 text-center">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  );
}


function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser
          ? 'bg-blue-600'
          : 'bg-gradient-to-br from-elzar-red to-orange-500'
      }`}>
        {isUser ? (
          <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" />
          </svg>
        ) : (
          <img src="/elzar.png" alt="Elzar" className="h-5 w-5 object-contain" />
        )}
      </div>

      {/* Message content */}
      <div className={`max-w-[80%] ${isUser ? 'text-right' : ''}`}>
        <div className={`rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-700 text-gray-100'
        }`}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Tool results (collapsed by default) */}
        {!isUser && message.tool_results && message.tool_results.length > 0 && (
          <div className="mt-1">
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-gray-500 hover:text-gray-300 transition-colors flex items-center gap-1"
            >
              <span>{expanded ? '▼' : '▶'}</span>
              <span>{message.tool_results.length} tool action{message.tool_results.length > 1 ? 's' : ''} used</span>
            </button>
            {expanded && (
              <div className="mt-1 space-y-1">
                {message.tool_results.map((result, idx) => (
                  <ToolResultBadge key={idx} result={result} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


function ToolResultBadge({ result }) {
  const [detailsOpen, setDetailsOpen] = useState(false);

  const toolIcons = {
    create_recipe: '🍳',
    search_recipes: '🔍',
    get_recipe: '📖',
    get_ideas_list: '💡',
    add_to_ideas_list: '➕',
    update_idea: '✏️',
    query_inventory: '📦',
    query_freezer: '🧊',
    create_prep_cook_session: '🥘',
    generate_shopping_list: '🛒',
    edit_recipe: '✏️',
    copy_and_edit_recipe: '📋',
    get_user_preferences: '👤',
    update_user_preferences: '👤',
    log_debrief: '📝',
    get_debriefs: '📊',
  };

  const icon = toolIcons[result.tool] || '🔧';
  const isSuccess = !result.error;

  return (
    <div className="text-xs">
      <button
        onClick={() => setDetailsOpen(!detailsOpen)}
        className={`flex items-center gap-1.5 px-2 py-1 rounded transition-colors ${
          isSuccess
            ? 'bg-gray-700/50 text-gray-400 hover:text-gray-200'
            : 'bg-red-900/30 text-red-400 hover:text-red-200'
        }`}
      >
        <span>{icon}</span>
        <span className="font-mono">{result.tool}</span>
        <span>{isSuccess ? '✓' : '✗'}</span>
      </button>
      {detailsOpen && result.result && (
        <pre className="mt-1 p-2 bg-gray-900 rounded text-[10px] text-gray-400 overflow-x-auto max-h-40 overflow-y-auto">
          {typeof result.result === 'string'
            ? result.result
            : JSON.stringify(result.result, null, 2)
          }
        </pre>
      )}
    </div>
  );
}


export default Chat;
