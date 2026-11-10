/**
 * Soil Testing Portal — Reusable API Client Helper
 * Handles CSRF memory caching, session authentication, JSON parsing,
 * multipart file uploads, binary PDF report streaming, and error handling.
 */

const API = (() => {
  // CSRF token stored strictly in application memory (never in localStorage or sessionStorage)
  let _csrfToken = null;

  /**
   * Fetches a fresh CSRF token from the backend.
   * If a token is already cached in memory, returns it unless forceRefresh is true.
   */
  async function getCsrfToken(forceRefresh = false) {
    if (_csrfToken && !forceRefresh) {
      return _csrfToken;
    }
    try {
      const response = await fetch('/api/auth/csrf-token', {
        method: 'GET',
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' },
      });
      if (!response.ok) {
        throw new Error('Failed to retrieve CSRF security token.');
      }
      const data = await response.json();
      _csrfToken = data.csrf_token;
      return _csrfToken;
    } catch (err) {
      console.error('CSRF Token fetch error:', err);
      throw err;
    }
  }

  /**
   * Clears the in-memory CSRF token (useful on logout or session reset).
   */
  function clearCsrfToken() {
    _csrfToken = null;
  }

  /**
   * Core request executor with standardized error handling and credentials.
   */
  async function request(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const headers = options.headers ? { ...options.headers } : {};

    // For state-changing operations, attach CSRF token header
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      const token = await getCsrfToken();
      if (token) {
        headers['X-CSRF-Token'] = token;
      }
    }

    // Set JSON Content-Type and Accept unless body is FormData (browser sets boundary for FormData)
    if (!(options.body instanceof FormData)) {
      if (!headers['Content-Type'] && options.body) {
        headers['Content-Type'] = 'application/json';
      }
      if (!headers['Accept']) {
        headers['Accept'] = 'application/json';
      }
    }

    const config = {
      ...options,
      method,
      headers,
      credentials: 'same-origin', // Passes Flask signed session cookies automatically
    };

    let response;
    try {
      response = await fetch(url, config);
    } catch (networkError) {
      console.error('Network error during API request:', networkError);
      throw {
        code: 'NETWORK_ERROR',
        message: 'Unable to reach the server. Please check your network connection.',
        status: 0,
      };
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return null;
    }

    // Parse JSON response body if present
    const contentType = response.headers.get('content-type') || '';
    let payload = null;
    if (contentType.includes('application/json')) {
      try {
        payload = await response.json();
      } catch (parseError) {
        payload = null;
      }
    }

    // If HTTP status is not ok (4xx, 5xx)
    if (!response.ok) {
      const errObj = {
        status: response.status,
        code: (payload && payload.error && payload.error.code) || 'REQUEST_FAILED',
        message: (payload && payload.error && payload.error.message) || `Request failed with status ${response.status}`,
        details: (payload && payload.error && payload.error.details) || null,
      };
      throw errObj;
    }

    return payload;
  }

  /**
   * Downloads a binary file (e.g. PDF report) and prompts browser save.
   */
  async function downloadFile(url, fallbackFilename = 'soil_report.pdf') {
    let response;
    try {
      response = await fetch(url, {
        method: 'GET',
        credentials: 'same-origin',
      });
    } catch (networkError) {
      throw {
        code: 'NETWORK_ERROR',
        message: 'Network error while attempting file download.',
        status: 0,
      };
    }

    if (!response.ok) {
      let message = 'Failed to download report.';
      try {
        const errJson = await response.json();
        if (errJson && errJson.error && errJson.error.message) {
          message = errJson.error.message;
        }
      } catch (_) {}
      throw {
        status: response.status,
        message,
      };
    }

    // Extract filename from Content-Disposition header if available
    let filename = fallbackFilename;
    const disposition = response.headers.get('content-disposition');
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename=["']?([^"';]+)["']?/i);
      if (match && match[1]) {
        filename = match[1].trim();
      }
    }

    const blob = await response.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = blobUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(blobUrl);
    return true;
  }

  // Convenience methods
  return {
    get: (url) => request(url, { method: 'GET' }),
    post: (url, data) => request(url, { method: 'POST', body: JSON.stringify(data) }),
    patch: (url, data) => request(url, { method: 'PATCH', body: JSON.stringify(data) }),
    upload: (url, formData) => request(url, { method: 'POST', body: formData }),
    download: (url, fallbackName) => downloadFile(url, fallbackName),
    getCsrfToken,
    clearCsrfToken,
    // Auth helpers
    checkAuth: () => request('/api/auth/me', { method: 'GET' }),
    logout: async () => {
      const res = await request('/api/auth/logout', { method: 'POST' });
      clearCsrfToken();
      return res;
    },
  };
})();

