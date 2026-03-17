import React, { useState, useEffect } from 'react';
import { getAllProfiles, createProfile, updateProfile, deleteProfile, getUserPreferences, updateUserPreferences } from '../api';

function Profiles() {
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingProfile, setEditingProfile] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // Form state
  const [formName, setFormName] = useState('');
  const [formRestrictions, setFormRestrictions] = useState('');

  // Household preferences state
  const [householdPrefs, setHouseholdPrefs] = useState('');
  const [householdPrefsSaved, setHouseholdPrefsSaved] = useState('');
  const [householdPrefsLoading, setHouseholdPrefsLoading] = useState(true);
  const [householdPrefsSaving, setHouseholdPrefsSaving] = useState(false);

  useEffect(() => {
    loadProfiles();
    loadHouseholdPrefs();
  }, []);

  const loadHouseholdPrefs = async () => {
    setHouseholdPrefsLoading(true);
    try {
      const data = await getUserPreferences();
      setHouseholdPrefs(data.content || '');
      setHouseholdPrefsSaved(data.content || '');
    } catch (err) {
      console.error('Failed to load household preferences:', err);
    } finally {
      setHouseholdPrefsLoading(false);
    }
  };

  const handleSaveHouseholdPrefs = async () => {
    setHouseholdPrefsSaving(true);
    try {
      const data = await updateUserPreferences(householdPrefs);
      setHouseholdPrefsSaved(data.content || '');
    } catch (err) {
      console.error('Failed to save household preferences:', err);
      alert('Failed to save household preferences');
    } finally {
      setHouseholdPrefsSaving(false);
    }
  };

  const householdPrefsChanged = householdPrefs !== householdPrefsSaved;

  const loadProfiles = async () => {
    setLoading(true);
    try {
      const data = await getAllProfiles();
      setProfiles(data);
    } catch (err) {
      console.error('Failed to load profiles:', err);
      alert('Failed to load profiles');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();

    if (!formName.trim() || !formRestrictions.trim()) {
      alert('Please fill in all fields');
      return;
    }

    try {
      await createProfile({
        name: formName.trim(),
        dietary_restrictions: formRestrictions.trim(),
      });

      setFormName('');
      setFormRestrictions('');
      setShowCreateForm(false);
      loadProfiles();
    } catch (err) {
      console.error('Failed to create profile:', err);
      alert(err.response?.data?.detail || 'Failed to create profile');
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();

    if (!formName.trim() || !formRestrictions.trim()) {
      alert('Please fill in all fields');
      return;
    }

    try {
      await updateProfile(editingProfile.id, {
        name: formName.trim(),
        dietary_restrictions: formRestrictions.trim(),
      });

      setFormName('');
      setFormRestrictions('');
      setEditingProfile(null);
      loadProfiles();
    } catch (err) {
      console.error('Failed to update profile:', err);
      alert(err.response?.data?.detail || 'Failed to update profile');
    }
  };

  const handleDelete = async (profileId) => {
    if (!confirm('Are you sure you want to delete this profile?')) return;

    try {
      await deleteProfile(profileId);
      loadProfiles();
    } catch (err) {
      console.error('Failed to delete profile:', err);
      alert('Failed to delete profile');
    }
  };

  const startEdit = (profile) => {
    setEditingProfile(profile);
    setFormName(profile.name);
    setFormRestrictions(profile.dietary_restrictions);
    setShowCreateForm(false);
  };

  const cancelEdit = () => {
    setEditingProfile(null);
    setFormName('');
    setFormRestrictions('');
  };

  const startCreate = () => {
    setShowCreateForm(true);
    setEditingProfile(null);
    setFormName('');
    setFormRestrictions('');
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Household Preferences */}
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg mb-6">
        <h2 className="text-2xl font-bold flex items-center mb-3">
          <span className="text-2xl mr-2">🏠</span>
          Household Preferences
        </h2>
        <p className="text-gray-400 text-sm mb-3">
          Shared preferences applied to every recipe and meal plan — things like where you shop,
          kitchen quirks, cooking schedule, or general household food philosophy.
        </p>

        {householdPrefsLoading ? (
          <div className="text-center py-4 text-gray-400">Loading...</div>
        ) : (
          <>
            <textarea
              value={householdPrefs}
              onChange={(e) => setHouseholdPrefs(e.target.value)}
              placeholder="e.g., Shop at Costco for proteins, Aldi for everything else. Oven runs 25° hot. Batch cook Sundays. Prefer leftovers that reheat well in a microwave."
              rows="4"
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 focus:ring-2 focus:ring-elzar-red text-gray-200 placeholder-gray-500"
              maxLength={4000}
            />
            <div className="flex justify-between items-center mt-2">
              <span className="text-xs text-gray-500">
                {householdPrefs.length} / 4,000
              </span>
              <button
                onClick={handleSaveHouseholdPrefs}
                disabled={!householdPrefsChanged || householdPrefsSaving}
                className={`px-5 py-1.5 rounded-lg text-sm transition-colors ${
                  householdPrefsChanged
                    ? 'bg-elzar-red hover:bg-red-600 text-white'
                    : 'bg-gray-600 text-gray-400 cursor-not-allowed'
                }`}
              >
                {householdPrefsSaving ? 'Saving...' : householdPrefsChanged ? 'Save' : 'Saved'}
              </button>
            </div>
          </>
        )}
      </div>

      {/* Person Profiles Section */}
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold flex items-center">
            <span className="text-3xl mr-2">👥</span>
            Household Members
          </h1>

          {!showCreateForm && !editingProfile && (
            <button
              onClick={startCreate}
              className="bg-elzar-red hover:bg-red-600 text-white px-4 py-2 rounded-lg transition-colors"
            >
              + Add Person
            </button>
          )}
        </div>

        {/* Create/Edit Form */}
        {(showCreateForm || editingProfile) && (
          <div className="bg-gray-700 rounded-lg p-6 mb-6">
            <h2 className="text-xl font-bold mb-4">
              {editingProfile ? 'Edit Profile' : 'Add Household Member'}
            </h2>

            <form onSubmit={editingProfile ? handleUpdate : handleCreate}>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">
                  Name *
                </label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="e.g., John, Sarah, Dad"
                  className="w-full bg-gray-600 border border-gray-500 rounded-lg px-4 py-2 focus:ring-2 focus:ring-elzar-red"
                  required
                />
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">
                  Preferences & Restrictions *
                </label>
                <textarea
                  value={formRestrictions}
                  onChange={(e) => setFormRestrictions(e.target.value)}
                  placeholder={"e.g., Gluten-free, allergic to tree nuts. Loves spicy food and bold flavors. Prefers high-protein meals. Dislikes corn (except in chili). Experienced cook but low effort tolerance on weeknights."}
                  rows="5"
                  className="w-full bg-gray-600 border border-gray-500 rounded-lg px-4 py-2 focus:ring-2 focus:ring-elzar-red"
                  required
                />
                <p className="text-xs text-gray-400 mt-1">
                  Include dietary restrictions, allergies, food preferences, cooking style, dislikes — anything that helps the AI cook for this person
                </p>
              </div>

              <div className="flex space-x-2">
                <button
                  type="submit"
                  className="bg-elzar-red hover:bg-red-600 text-white px-6 py-2 rounded-lg transition-colors"
                >
                  {editingProfile ? 'Update' : 'Create'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateForm(false);
                    cancelEdit();
                  }}
                  className="bg-gray-600 hover:bg-gray-500 text-white px-6 py-2 rounded-lg transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Profiles List */}
        {loading && (
          <div className="text-center py-12 text-gray-400">
            Loading profiles...
          </div>
        )}

        {!loading && profiles.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            <p className="text-5xl mb-4">👤</p>
            <p className="text-lg">No household members yet</p>
            <p className="mt-2">Add people to personalize recipes with their preferences and restrictions</p>
          </div>
        )}

        {!loading && profiles.length > 0 && (
          <div className="space-y-4">
            {profiles.map((profile) => (
              <div
                key={profile.id}
                className="bg-gray-700 rounded-lg p-4 hover:bg-gray-650 transition-colors"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="text-xl font-bold mb-2">{profile.name}</h3>
                    <p className="text-gray-300 mb-2 whitespace-pre-line">{profile.dietary_restrictions}</p>
                    <p className="text-xs text-gray-500">
                      Created: {new Date(profile.created_at).toLocaleDateString()}
                      {profile.updated_at !== profile.created_at && (
                        <> • Updated: {new Date(profile.updated_at).toLocaleDateString()}</>
                      )}
                    </p>
                  </div>

                  <div className="flex space-x-2 ml-4">
                    <button
                      onClick={() => startEdit(profile)}
                      className="bg-elzar-orange hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-sm transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(profile.id)}
                      className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm transition-colors"
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

      <div className="mt-6 bg-gray-800 rounded-lg p-6 shadow-lg">
        <h2 className="text-xl font-bold mb-4">ℹ️ How Profiles Work</h2>
        <div className="text-gray-300 space-y-2">
          <p>
            • <strong>Household Preferences</strong> are always active — they shape every recipe and meal plan
          </p>
          <p>
            • <strong>Person profiles</strong> can be toggled on/off per recipe on the Generator page
          </p>
          <p>
            • Include anything that helps the AI: dietary restrictions, allergies, food likes/dislikes, cooking style, calorie goals
          </p>
          <p>
            • The more detail you provide, the better the AI will tailor recipes to your household
          </p>
        </div>
      </div>
    </div>
  );
}

export default Profiles;
