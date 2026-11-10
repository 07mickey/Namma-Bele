/**
 * Environment configuration for NAMMA BELE Frontend
 * Uses same-origin relative base URL when running in browser
 */
const CONFIG = {
  API_BASE_URL: (typeof window !== 'undefined') ? '' : 'http://127.0.0.1:5000',
  APP_NAME: 'Soil Testing Portal',
  SESSION_KEY: 'soil_farmer_session'
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = CONFIG;
}
