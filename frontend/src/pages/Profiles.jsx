import React, { useState, useEffect } from 'react';
import { getAllProfiles, createProfile, updateProfile, deleteProfile } from '../api';

function Profiles() {
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingProfile, setEditingProfile] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  
  // Form state
  const [formName, setFormName] = useState('');
  const [formRestrictions, setFormRestrictions] = useState('');

  useEffect(() => {
    loadProfiles();
  }, []);

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
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold flex items-center">
            <span className="text-3xl mr-2">👥</span>
            Household Dietary Profiles
          </h1>
          
          {!showCreateForm && !editingProfile && (
            <button
              onClick={startCreate}
              className="bg-elzar-red hover:bg-red-600 text-white px-4 py-2 rounded-lg transition-colors"
            >
              + Add Profile
            </button>
          )}
        </div>

        {/* Create/Edit Form */}
        {(showCreateForm || editingProfile) && (
          <div className="bg-gray-700 rounded-lg p-6 mb-6">
            <h2 className="text-xl font-bold mb-4">
              {editingProfile ? 'Edit Profile' : 'Create New Profile'}
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
                  Dietary Restrictions *
                </label>
                <textarea
                  value={formRestrictions}
                  onChange={(e) => setFormRestrictions(e.target.value)}
                  placeholder="e.g., Gluten-free, lactose intolerant, vegetarian, allergic to nuts"
                  rows="4"
                  className="w-full bg-gray-600 border border-gray-500 rounded-lg px-4 py-2 focus:ring-2 focus:ring-elzar-red"
                  required
                />
                <p className="text-xs text-gray-400 mt-1">
                  Describe any allergies, intolerances, or dietary preferences
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
            <p className="text-lg">No profiles yet</p>
            <p className="mt-2">Create a profile to track dietary restrictions for household members</p>
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
                    <p className="text-gray-300 mb-2">{profile.dietary_restrictions}</p>
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
            • Create profiles for each person in your household with their dietary restrictions
          </p>
          <p>
            • On the Generator page, toggle which household members will be eating the meal
          </p>
          <p>
            • The recipe will be generated taking into account all active profiles' restrictions
          </p>
          <p>
            • Examples: "Gluten-free", "Vegan", "Allergic to shellfish", "Low sodium diet"
          </p>
        </div>
      </div>
    </div>
  );
}

export default Profiles;

