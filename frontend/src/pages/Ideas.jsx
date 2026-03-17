import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getIdeas, createIdea, updateIdea, deleteIdea } from '../api';

const STATUS_OPTIONS = [
  { value: 'idea', label: 'Idea', color: 'bg-blue-600' },
  { value: 'planned', label: 'Planned', color: 'bg-yellow-600' },
  { value: 'tested', label: 'Tested', color: 'bg-green-600' },
  { value: 'favorite', label: 'Favorite', color: 'bg-purple-600' },
];

function Ideas() {
  const navigate = useNavigate();
  const [ideas, setIdeas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // Filters
  const [filterStatus, setFilterStatus] = useState('');
  const [filterSearch, setFilterSearch] = useState('');

  // Form state (shared for create and edit)
  const [formName, setFormName] = useState('');
  const [formNotes, setFormNotes] = useState('');
  const [formTags, setFormTags] = useState('');
  const [formCalories, setFormCalories] = useState('');
  const [formStatus, setFormStatus] = useState('idea');

  useEffect(() => {
    loadIdeas();
  }, [filterStatus, filterSearch]);

  const loadIdeas = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterStatus) params.status = filterStatus;
      if (filterSearch) params.search = filterSearch;
      const data = await getIdeas(params);
      setIdeas(data);
    } catch (err) {
      console.error('Failed to load ideas:', err);
    } finally {
      setLoading(false);
    }
  };

  const parseTags = (tagString) => {
    return tagString
      .split(',')
      .map(t => t.trim())
      .filter(t => t.length > 0);
  };

  const resetForm = () => {
    setFormName('');
    setFormNotes('');
    setFormTags('');
    setFormCalories('');
    setFormStatus('idea');
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!formName.trim()) return;

    try {
      await createIdea({
        name: formName.trim(),
        notes: formNotes.trim(),
        tags: parseTags(formTags),
        calorie_estimate: formCalories.trim() || null,
        status: formStatus,
      });
      resetForm();
      setShowCreateForm(false);
      loadIdeas();
    } catch (err) {
      console.error('Failed to create idea:', err);
      alert(err.response?.data?.detail || 'Failed to create idea');
    }
  };

  const startEdit = (idea) => {
    setEditingId(idea.id);
    setFormName(idea.name);
    setFormNotes(idea.notes || '');
    setFormTags(idea.tags.join(', '));
    setFormCalories(idea.calorie_estimate || '');
    setFormStatus(idea.status);
    setShowCreateForm(false);
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    if (!formName.trim()) return;

    try {
      await updateIdea(editingId, {
        name: formName.trim(),
        notes: formNotes.trim(),
        tags: parseTags(formTags),
        calorie_estimate: formCalories.trim() || null,
        status: formStatus,
      });
      setEditingId(null);
      resetForm();
      loadIdeas();
    } catch (err) {
      console.error('Failed to update idea:', err);
      alert(err.response?.data?.detail || 'Failed to update idea');
    }
  };

  const handleStatusChange = async (ideaId, newStatus) => {
    try {
      await updateIdea(ideaId, { status: newStatus });
      setIdeas(prev => prev.map(i =>
        i.id === ideaId ? { ...i, status: newStatus } : i
      ));
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const handleDelete = async (ideaId) => {
    if (!confirm('Delete this idea?')) return;
    try {
      await deleteIdea(ideaId);
      if (editingId === ideaId) {
        setEditingId(null);
        resetForm();
      }
      loadIdeas();
    } catch (err) {
      console.error('Failed to delete idea:', err);
      alert('Failed to delete idea');
    }
  };

  const promoteToRecipe = (idea) => {
    navigate('/generator', {
      state: {
        promotedIdea: {
          name: idea.name,
          notes: idea.notes,
          calorie_estimate: idea.calorie_estimate,
          tags: idea.tags,
        }
      }
    });
  };

  const getStatusBadge = (statusValue) => {
    const opt = STATUS_OPTIONS.find(s => s.value === statusValue);
    if (!opt) return null;
    return (
      <span className={`${opt.color} text-white text-xs px-2 py-0.5 rounded`}>
        {opt.label}
      </span>
    );
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold flex items-center">
            <span className="text-3xl mr-2">💡</span>
            Ideas
          </h1>
          {!showCreateForm && editingId === null && (
            <button
              onClick={() => { setShowCreateForm(true); resetForm(); }}
              className="bg-elzar-red hover:bg-red-600 text-white px-4 py-2 rounded-lg transition-colors"
            >
              + Add Idea
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="flex gap-3 mb-6">
          <input
            type="text"
            value={filterSearch}
            onChange={(e) => setFilterSearch(e.target.value)}
            placeholder="Search ideas..."
            className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-elzar-red"
          />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-elzar-red"
          >
            <option value="">All Status</option>
            {STATUS_OPTIONS.map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>

        {/* Create/Edit Form */}
        {(showCreateForm || editingId !== null) && (
          <div className="bg-gray-700 rounded-lg p-5 mb-6">
            <h2 className="text-lg font-bold mb-3">
              {editingId !== null ? 'Edit Idea' : 'New Idea'}
            </h2>
            <form onSubmit={editingId !== null ? handleUpdate : handleCreate} className="space-y-3">
              <div>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="Idea name (e.g., Egg Roll in a Bowl)"
                  className="w-full bg-gray-600 border border-gray-500 rounded px-3 py-2 focus:ring-2 focus:ring-elzar-red"
                  required
                  autoFocus
                />
              </div>
              <div>
                <textarea
                  value={formNotes}
                  onChange={(e) => setFormNotes(e.target.value)}
                  placeholder="Notes (optional) — recipe ideas, links, inspiration..."
                  rows="3"
                  className="w-full bg-gray-600 border border-gray-500 rounded px-3 py-2 focus:ring-2 focus:ring-elzar-red"
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium mb-1">Tags (comma-separated)</label>
                  <input
                    type="text"
                    value={formTags}
                    onChange={(e) => setFormTags(e.target.value)}
                    placeholder="e.g., freezer-friendly, low-cal, cheat-day"
                    className="w-full bg-gray-600 border border-gray-500 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-elzar-red"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Calorie estimate</label>
                  <input
                    type="text"
                    value={formCalories}
                    onChange={(e) => setFormCalories(e.target.value)}
                    placeholder="e.g., 300-400 or ~500"
                    className="w-full bg-gray-600 border border-gray-500 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-elzar-red"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Status</label>
                  <select
                    value={formStatus}
                    onChange={(e) => setFormStatus(e.target.value)}
                    className="w-full bg-gray-600 border border-gray-500 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-elzar-red"
                  >
                    {STATUS_OPTIONS.map(s => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  type="submit"
                  className="bg-elzar-red hover:bg-red-600 text-white px-5 py-2 rounded-lg transition-colors"
                >
                  {editingId !== null ? 'Update' : 'Add'}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowCreateForm(false); setEditingId(null); resetForm(); }}
                  className="bg-gray-600 hover:bg-gray-500 text-white px-5 py-2 rounded-lg transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Ideas List */}
        {loading && (
          <div className="text-center py-12 text-gray-400">Loading ideas...</div>
        )}

        {!loading && ideas.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            <p className="text-5xl mb-4">💡</p>
            <p className="text-lg">No ideas yet</p>
            <p className="mt-2">Add meal ideas to brainstorm between planning sessions</p>
          </div>
        )}

        {!loading && ideas.length > 0 && (
          <div className="space-y-3">
            {ideas.map((idea) => (
              <div
                key={idea.id}
                className={`bg-gray-700 rounded-lg p-4 transition-colors ${
                  editingId === idea.id ? 'ring-2 ring-elzar-red' : 'hover:bg-gray-650'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-lg font-bold">{idea.name}</h3>
                      {getStatusBadge(idea.status)}
                      {idea.calorie_estimate && (
                        <span className="text-xs text-gray-400">🔥 {idea.calorie_estimate} cal</span>
                      )}
                    </div>
                    {idea.notes && (
                      <p className="text-gray-300 text-sm mb-2 whitespace-pre-line">{idea.notes}</p>
                    )}
                    {idea.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-2">
                        {idea.tags.map((tag, i) => (
                          <span
                            key={i}
                            className="bg-gray-600 text-gray-300 text-xs px-2 py-0.5 rounded cursor-pointer hover:bg-gray-500"
                            onClick={() => setFilterSearch(tag)}
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                    <p className="text-xs text-gray-500">
                      Added: {new Date(idea.created_at).toLocaleDateString()}
                      {idea.updated_at !== idea.created_at && (
                        <> • Updated: {new Date(idea.updated_at).toLocaleDateString()}</>
                      )}
                    </p>
                  </div>

                  <div className="flex flex-col gap-1 ml-3">
                    {/* Quick status cycle */}
                    <select
                      value={idea.status}
                      onChange={(e) => handleStatusChange(idea.id, e.target.value)}
                      className="bg-gray-600 border border-gray-500 rounded px-2 py-1 text-xs"
                    >
                      {STATUS_OPTIONS.map(s => (
                        <option key={s.value} value={s.value}>{s.label}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => promoteToRecipe(idea)}
                      className="bg-green-700 hover:bg-green-600 text-white px-2 py-1 rounded text-xs transition-colors"
                      title="Generate a recipe from this idea"
                    >
                      🍳 Cook it
                    </button>
                    <button
                      onClick={() => startEdit(idea)}
                      className="bg-elzar-orange hover:bg-orange-600 text-white px-2 py-1 rounded text-xs transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(idea.id)}
                      className="bg-red-700 hover:bg-red-600 text-white px-2 py-1 rounded text-xs transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Ideas;
