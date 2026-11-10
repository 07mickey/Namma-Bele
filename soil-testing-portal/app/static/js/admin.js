/**
 * Admin API & Session Management for Soil Testing Portal
 * Powering Person 3's Admin Control Center & Coordinator workflows.
 */

const ADMIN_SESSION_KEY = 'soil_admin_session';

const Admin = {
  // Session storage helpers
  saveAdminSession(token, admin) {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(ADMIN_SESSION_KEY, JSON.stringify({
        token,
        admin,
        loginTime: new Date().toISOString()
      }));
    } catch (e) {
      console.warn('Storage error:', e);
    }
  },

  getAdminSession() {
    if (typeof window === 'undefined') return null;
    try {
      const raw = localStorage.getItem(ADMIN_SESSION_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  },

  getAdminToken() {
    return this.getAdminSession()?.token || null;
  },

  getAdminProfile() {
    return this.getAdminSession()?.admin || null;
  },

  isAdminLoggedIn() {
    return !!this.getAdminToken();
  },

  clearAdminSession() {
    if (typeof window === 'undefined') return;
    try {
      localStorage.removeItem(ADMIN_SESSION_KEY);
    } catch (e) {}
  },

  async adminLogout() {
    this.clearAdminSession();
    if (typeof Auth !== 'undefined') {
      Auth.clearSession();
    }
    try {
      const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-CSRF-Token': csrf }
      });
    } catch (e) {}
    window.location.href = '/login?logged_out=1';
  },

  requireAdminAuth(redirectPath = '/admin-login') {
    if (typeof window === 'undefined') return true;
    try {
      const urlParams = new URLSearchParams(window.location.search);
      if (!this.isAdminLoggedIn() && (urlParams.get('demo') === '1' || urlParams.get('preview') === '1')) {
        this.saveAdminSession('demo-admin-token', { username: 'admin', role: 'Chief Agricultural Coordinator' });
      }
    } catch (e) {}
    // If Auth is defined and user role is admin, sync to Admin session
    if (!this.isAdminLoggedIn() && typeof Auth !== 'undefined' && Auth.getSession()) {
      const user = Auth.getFarmer();
      if (user && user.role === 'admin') {
        this.saveAdminSession(Auth.getToken() || 'admin-token', user);
      }
    }
    if (!this.isAdminLoggedIn()) {
      window.location.href = redirectPath;
      return false;
    }
    return true;
  },

  redirectIfAdminLoggedIn(redirectPath = 'admin-dashboard.html') {
    if (typeof window === 'undefined') return;
    if (this.isAdminLoggedIn()) {
      window.location.href = redirectPath;
    }
  },

  getBaseUrl() {
    if (typeof CONFIG !== 'undefined' && CONFIG.API_BASE_URL !== undefined) {
      return CONFIG.API_BASE_URL;
    }
    return (typeof window !== 'undefined') ? '' : 'http://127.0.0.1:5000';
  },

  async adminRequest(endpoint, options = {}) {
    const url = `${this.getBaseUrl()}${endpoint}`;
    const headers = {
      ...(options.headers || {})
    };

    // Attach Bearer token
    if (this.getAdminToken() && !options.skipAuth) {
      headers['Authorization'] = `Bearer ${this.getAdminToken()}`;
    }

    // Attach CSRF token if present
    const method = (options.method || 'GET').toUpperCase();
    const isMutation = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);
    if (isMutation) {
      if (typeof document !== 'undefined') {
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfMeta && csrfMeta.content) {
          headers['X-CSRF-Token'] = csrfMeta.content;
        }
      }
      if (!headers['X-CSRF-Token']) {
        try {
          const tRes = await fetch(`${this.getBaseUrl()}/api/auth/csrf-token`, { credentials: 'include' });
          if (tRes.ok) {
            const tData = await tRes.json();
            if (tData && tData.csrf_token) {
              headers['X-CSRF-Token'] = tData.csrf_token;
              const meta = typeof document !== 'undefined' ? document.querySelector('meta[name="csrf-token"]') : null;
              if (meta) meta.content = tData.csrf_token;
            }
          }
        } catch (e) {}
      }
    }
    options.credentials = options.credentials || 'include';

    // Auto-attach Content-Type if JSON payload (and not FormData)
    if (options.body && !(options.body instanceof (typeof FormData !== 'undefined' ? FormData : Object))) {
      if (!headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
      }
    }

    try {
      let response = await fetch(url, {
        ...options,
        headers
      });

      let data = {};
      try {
        data = await response.json();
      } catch (err) {
        data = {};
      }

      // Proactively recover from stale or missing CSRF token once
      if (response.status === 403 && (data?.error?.code === 'CSRF_ERROR' || data?.error === 'CSRF_ERROR') && !options._csrfRetried) {
        try {
          const tRes = await fetch(`${this.getBaseUrl()}/api/auth/csrf-token`, { credentials: 'include' });
          if (tRes.ok) {
            const tData = await tRes.json();
            if (tData && tData.csrf_token) {
              headers['X-CSRF-Token'] = tData.csrf_token;
              const meta = typeof document !== 'undefined' ? document.querySelector('meta[name="csrf-token"]') : null;
              if (meta) meta.content = tData.csrf_token;
              return await this.adminRequest(endpoint, { ...options, headers, _csrfRetried: true });
            }
          }
        } catch (e) {}
      }

      if (response.status === 401 && !options.skipAuth) {
        this.clearAdminSession();
        if (typeof window !== 'undefined' && !window.location.pathname.endsWith('admin-login.html')) {
          window.location.href = 'admin-login.html?session_expired=1';
        }
        return { ok: false, status: 401, error: 'Admin session expired. Please sign in again.' };
      }

      if (!response.ok) {
        return {
          ok: false,
          status: response.status,
          error: data.message || data.error || `Server responded with status ${response.status}`
        };
      }

      return { ok: true, status: response.status, data };
    } catch (networkError) {
      console.warn(`[Admin API Notice] Request to ${url} failed:`, networkError);
      return {
        ok: false,
        offline: true,
        error: `Notice: Backend server is offline at ${this.getBaseUrl()}. Please ensure Person 1's Flask backend is running.`
      };
    }
  },

  // 1. Admin Login
  async adminLogin({ username, password }) {
    const res = await this.adminRequest('/api/admin/login', {
      method: 'POST',
      skipAuth: true,
      body: JSON.stringify({ username, password })
    });
    if (res.offline) {
      return {
        ok: true,
        offlineDemo: true,
        data: {
          token: 'demo-admin-token',
          admin: { username: username || 'admin', role: 'Chief Agricultural Coordinator' }
        }
      };
    }
    return res;
  },

  // 2. Fetch all appointments across farmers
  async getAppointments() {
    const res = await this.adminRequest('/api/admin/appointments', {
      method: 'GET'
    });
    if (res.offline) {
      const store = typeof DemoStore !== 'undefined' ? DemoStore : (typeof require !== 'undefined' ? require('./api.js').DemoStore : null);
      if (store) {
        return {
          ok: true,
          offlineDemo: true,
          data: { appointments: store.getAppointments() }
        };
      }
    }
    return res;
  },

  // 3. Update appointment status (Pending -> Approved / Rejected -> Completed)
  async updateAppointmentStatus(appointmentId, status) {
    const validStatuses = ['Pending', 'Approved', 'Rejected', 'Completed'];
    if (!validStatuses.includes(status)) {
      return { ok: false, error: `Invalid status: ${status}. Must be one of: ${validStatuses.join(', ')}` };
    }

    const res = await this.adminRequest(`/api/admin/appointments/${appointmentId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status })
    });
    if (res.offline) {
      const store = typeof DemoStore !== 'undefined' ? DemoStore : (typeof require !== 'undefined' ? require('./api.js').DemoStore : null);
      if (store) {
        store.updateStatus(appointmentId, status);
        return {
          ok: true,
          offlineDemo: true,
          message: `Appointment #${appointmentId} status updated to ${status} in preview mode.`
        };
      }
    }
    return res;
  },

  // 4. Upload Soil Test PDF Report
  async uploadReport(formData) {
    // Note: Do not set Content-Type header when passing FormData, fetch sets boundary automatically
    const res = await this.adminRequest('/api/admin/reports/upload', {
      method: 'POST',
      body: formData
    });
    if (res.offline) {
      const store = typeof DemoStore !== 'undefined' ? DemoStore : (typeof require !== 'undefined' ? require('./api.js').DemoStore : null);
      if (store) {
        let appointmentId = 101;
        let remarks = 'Soil test report verified.';
        if (formData && typeof formData.get === 'function') {
          appointmentId = formData.get('appointment_id') || 101;
          remarks = formData.get('remarks') || remarks;
        }
        const newReport = store.addReport({
          appointment_id: Number(appointmentId),
          remarks,
          file_name: `soil_report_${appointmentId}.pdf`
        });
        return {
          ok: true,
          offlineDemo: true,
          data: { report: newReport },
          message: 'Report uploaded and appointment marked completed in preview mode.'
        };
      }
    }
    return res;
  },

  // 5. Fetch all reports
  async getReports() {
    const res = await this.adminRequest('/api/admin/reports', {
      method: 'GET'
    });
    if (res.offline) {
      const store = typeof DemoStore !== 'undefined' ? DemoStore : (typeof require !== 'undefined' ? require('./api.js').DemoStore : null);
      if (store) {
        return {
          ok: true,
          offlineDemo: true,
          data: { reports: store.getReports() }
        };
      }
    }
    return res;
  },

  // 6. Fetch registered farmers list
  async getFarmers() {
    const res = await this.adminRequest('/api/admin/farmers', {
      method: 'GET'
    });
    if (res.offline) {
      const store = typeof DemoStore !== 'undefined' ? DemoStore : (typeof require !== 'undefined' ? require('./api.js').DemoStore : null);
      if (store) {
        return {
          ok: true,
          offlineDemo: true,
          data: { farmers: store.getFarmers() }
        };
      }
    }
    return res;
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = Admin;
}
if (typeof window !== 'undefined') {
  window.Admin = Admin;
}

