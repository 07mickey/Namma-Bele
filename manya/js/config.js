/**
 * Environment configuration for Farmer Frontend
 * Defaults to Person 1's Flask API server at http://127.0.0.1:5000
 */
const CONFIG = {
  API_BASE_URL: (typeof window !== 'undefined' && window.API_BASE_URL) ? window.API_BASE_URL : 'http://127.0.0.1:5000',
  APP_NAME: 'Soil Testing Portal',
  SESSION_KEY: 'soil_farmer_session'
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = CONFIG;
}
