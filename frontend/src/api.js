import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Recipe APIs
export const generateRecipe = async (params) => {
  const response = await api.post('/api/recipes/generate', params);
  return response.data;
};

export const regenerateRecipe = async (recipeId) => {
  const response = await api.post(`/api/recipes/regenerate/${recipeId}`);
  return response.data;
};

export const getRecipe = async (recipeId) => {
  const response = await api.get(`/api/recipes/${recipeId}`);
  return response.data;
};

export const downloadRecipe = async (recipeId) => {
  const response = await api.get(`/api/recipes/${recipeId}/download`, {
    responseType: 'blob',
  });
  return response.data;
};

export const sendRecipeNotification = async (recipeId, title = 'Recipe from Elzar') => {
  const response = await api.post(`/api/recipes/${recipeId}/send`, { title });
  return response.data;
};

// History APIs
export const getRecipeHistory = async (params = {}) => {
  const response = await api.get('/api/history/', { params });
  return response.data;
};

export const deleteRecipe = async (recipeId) => {
  const response = await api.delete(`/api/history/${recipeId}`);
  return response.data;
};

export const getRecipeCount = async () => {
  const response = await api.get('/api/history/count');
  return response.data;
};

// Profile APIs
export const getAllProfiles = async () => {
  const response = await api.get('/api/profiles/');
  return response.data;
};

export const getProfile = async (profileId) => {
  const response = await api.get(`/api/profiles/${profileId}`);
  return response.data;
};

export const createProfile = async (profileData) => {
  const response = await api.post('/api/profiles/', profileData);
  return response.data;
};

export const updateProfile = async (profileId, profileData) => {
  const response = await api.put(`/api/profiles/${profileId}`, profileData);
  return response.data;
};

export const deleteProfile = async (profileId) => {
  const response = await api.delete(`/api/profiles/${profileId}`);
  return response.data;
};

// Settings APIs
export const getConfig = async () => {
  const response = await api.get('/api/settings/config');
  return response.data;
};

export const getAllSettings = async () => {
  const response = await api.get('/api/settings/');
  return response.data;
};

export const getSetting = async (key) => {
  const response = await api.get(`/api/settings/${key}`);
  return response.data;
};

export const setSetting = async (key, value) => {
  const response = await api.put(`/api/settings/${key}`, { value });
  return response.data;
};

export const testGrocyConnection = async () => {
  const response = await api.get('/api/settings/test/grocy');
  return response.data;
};

export const testLLMConnection = async () => {
  const response = await api.get('/api/settings/test/llm');
  return response.data;
};

export default api;

