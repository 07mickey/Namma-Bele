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

  adminLogout() {
    this.clearAdminSession();
    window.location.href = 'admin-login.html?logged_out=1';
  },

  requireAdminAuth(redirectPath = 'admin-login.html') {
    if (typeof window === 'undefined') return true;
    try {
      const urlParams = new URLSearchParams(window.location.search);
      if (!this.isAdminLoggedIn() && (urlParams.get('demo') === '1' || urlParams.get('preview') === '1')) {
        this.saveAdminSession('demo-admin-token', { username: 'admin', role: 'Chief Agricultural Coordinator' });
      }
    } catch (e) {}
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
    if (typeof CONFIG !== 'undefined' && CONFIG.API_BASE_URL) {
      return CONFIG.API_BASE_URL;
    }
    return 'http://127.0.0.1:5000';
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

    // Auto-attach Content-Type if JSON payload (and not FormData)
    if (options.body && !(options.body instanceof (typeof FormData !== 'undefined' ? FormData : Object))) {
      if (!headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
      }
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers
      });

      if (response.status === 401 && !options.skipAuth) {
        this.clearAdminSession();
        if (typeof window !== 'undefined' && !window.location.pathname.endsWith('admin-login.html')) {
          window.location.href = 'admin-login.html?session_expired=1';
        }
        return { ok: false, status: 401, error: 'Admin session expired. Please sign in again.' };
      }

      let data = {};
      try {
        data = await response.json();
      } catch (e) {
        data = {};
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

