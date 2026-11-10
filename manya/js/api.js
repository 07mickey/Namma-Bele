/**
 * Centralized API service for Farmer Frontend
 * Communicates with Person 1's Flask Backend at CONFIG.API_BASE_URL.
 * Gracefully provides an interactive Demo Sandbox when backend is offline.
 */

// Local Demo Store for seamless client-side preview when backend is offline
const DemoStore = {
  _mem: {},
  _getItem(key) {
    if (typeof localStorage !== 'undefined') {
      try { return localStorage.getItem(key); } catch (e) {}
    }
    return this._mem[key] || null;
  },
  _setItem(key, val) {
    if (typeof localStorage !== 'undefined') {
      try { localStorage.setItem(key, val); } catch (e) {}
    }
    this._mem[key] = val;
  },

  getAppointments() {
    try {
      const data = this._getItem('soil_demo_appointments');
      if (data) return JSON.parse(data);
    } catch (e) {}

    const initial = [
      {
        id: 101,
        land_details: 'Survey No. 42, North Acre (3.5 Acres)',
        address: 'Someshwar Village, Plot 4B, District Hubli',
        preferred_date: '2026-11-10',
        preferred_time: 'Morning (8:00 AM - 12:00 PM)',
        status: 'Pending',
        notes: 'Cotton crop planned. Need nitrogen and organic carbon analysis.',
        created_at: new Date().toISOString()
      },
      {
        id: 102,
        land_details: 'Plot 18, West Canal Field (2 Acres)',
        address: 'Someshwar Rural Road, Near Primary Health Center',
        preferred_date: '2026-11-14',
        preferred_time: 'Afternoon (1:00 PM - 5:00 PM)',
        status: 'Approved',
        notes: 'Sugarcane plantation. Water drainage is moderate.',
        created_at: new Date(Date.now() - 86400000).toISOString()
      },
      {
        id: 103,
        land_details: 'Survey No. 88, River Basin (5 Acres)',
        address: 'Belagavi Rural Sector, Near River Bank',
        preferred_date: '2026-10-24',
        preferred_time: 'Morning (8:00 AM - 12:00 PM)',
        status: 'Completed',
        notes: 'Paddy harvest concluded. Preparing for Rabi sowing.',
        created_at: new Date(Date.now() - 604800000).toISOString()
      },
      {
        id: 104,
        land_details: 'Survey No. 12, Hill Ridge (1.5 Acres)',
        address: 'Bhairidevarakoppa Rural Sector',
        preferred_date: '2026-10-18',
        preferred_time: 'Afternoon (1:00 PM - 5:00 PM)',
        status: 'Rejected',
        notes: 'Requested date overlaps with regional festival holiday. Rescheduled to Nov 15.',
        created_at: new Date(Date.now() - 1209600000).toISOString()
      }
    ];
    this.saveAppointments(initial);
    return initial;
  },

  saveAppointments(list) {
    try {
      this._setItem('soil_demo_appointments', JSON.stringify(list));
    } catch (e) {}
  },

  addAppointment(apt) {
    const list = this.getAppointments();
    const newId = list.length ? Math.max(...list.map(a => a.id || 100)) + 1 : 101;
    const newApt = {
      id: newId,
      ...apt,
      status: 'Pending',
      created_at: new Date().toISOString()
    };
    list.unshift(newApt);
    this.saveAppointments(list);
    return newApt;
  },

  updateStatus(id, newStatus) {
    const list = this.getAppointments();
    const item = list.find(a => String(a.id) === String(id));
    if (item) {
      item.status = newStatus;
      this.saveAppointments(list);
      return true;
    }
    return false;
  },

  getReports() {
    try {
      const data = this._getItem('soil_demo_reports');
      if (data) return JSON.parse(data);
    } catch (e) {}

    const initial = [
      {
        id: 201,
        appointment_id: 103,
        land_details: 'Survey No. 88, River Basin (5 Acres)',
        report_date: '2026-10-28',
        file_name: 'soil_health_certificate_103.pdf',
        remarks: 'pH 6.85 (Neutral Loam). Adequate Phosphorus (18.4 kg/ha), Medium Nitrogen (215 kg/ha). Recommended 45kg Urea split application.'
      },
      {
        id: 202,
        appointment_id: 99,
        land_details: 'Plot 04, East Orchard (2.5 Acres)',
        report_date: '2026-10-12',
        file_name: 'soil_health_certificate_99.pdf',
        remarks: 'pH 7.1 (Slightly Alkaline). High Potassium (340 kg/ha), High Organic Carbon (0.75%). Optimal for Rabi horticulture.'
      }
    ];
    this.saveReports(initial);
    return initial;
  },

  saveReports(list) {
    try {
      this._setItem('soil_demo_reports', JSON.stringify(list));
    } catch (e) {}
  },

  addReport(report) {
    const list = this.getReports();
    const newId = list.length ? Math.max(...list.map(r => r.id || 200)) + 1 : 201;
    const newReport = {
      id: newId,
      ...report,
      report_date: report.report_date || new Date().toISOString().split('T')[0]
    };
    list.unshift(newReport);
    this.saveReports(list);

    // Also mark associated appointment as Completed
    if (report.appointment_id) {
      this.updateStatus(report.appointment_id, 'Completed');
    }
    return newReport;
  },

  getFarmers() {
    return [
      { id: 1, name: 'Ramesh Patil', phone: '9876543210', created_at: '2026-10-15' },
      { id: 2, name: 'Suresh Kumar', phone: '9822334455', created_at: '2026-10-18' },
      { id: 3, name: 'Anand Deshmukh', phone: '9844556677', created_at: '2026-10-22' }
    ];
  },

  // Generates a mock printable PDF blob
  generateSamplePdfBlob(reportId = '103') {
    const sampleContent = `%PDF-1.4
1 0 obj
<< /Title (Official Soil Health Card)
   /Author (Taluk Agricultural Testing Laboratory)
   /Subject (Soil Fertility Analysis Report) >>
endobj
2 0 obj
<< /Type /Catalog
   /Pages 3 0 R >>
endobj
3 0 obj
<< /Type /Pages
   /Kids [4 0 R]
   /Count 1 >>
endobj
4 0 obj
<< /Type /Page
   /Parent 3 0 R
   /MediaBox [0 0 612 792]
   /Resources << /Font << /F1 5 0 R >> >>
   /Contents 6 0 R >>
endobj
5 0 obj
<< /Type /Font
   /Subtype /Type1
   /BaseFont /Helvetica >>
endobj
6 0 obj
<< /Length 580 >>
stream
BT
/F1 18 Tf
50 720 Td
(COMMUNITY AGRICULTURAL SOIL HEALTH CARD) Tj
/F1 11 Tf
0 -30 Td
(Official Laboratory Certificate ID: #REPORT-${reportId}) Tj
0 -20 Td
(Status: Verified & Certified by Taluk Agricultural Extension Office) Tj
0 -30 Td
(--- CERTIFIED LABORATORY TEST RESULTS ---) Tj
0 -20 Td
(Available Nitrogen [N]: 215 kg/ha  [Status: Medium]) Tj
0 -20 Td
(Available Phosphorus [P]: 18.4 kg/ha  [Status: Adequate]) Tj
0 -20 Td
(Available Potassium [K]: 310 kg/ha  [Status: High]) Tj
0 -20 Td
(Soil Reaction [pH]: 6.85  [Status: Neutral Loam - Optimal]) Tj
0 -20 Td
(Organic Carbon [OC]: 0.62%  [Status: Moderate/Healthy]) Tj
0 -30 Td
(--- OFFICIAL AGRONOMIC RECOMMENDATION ---) Tj
0 -20 Td
(Apply 45kg Urea split at 30 and 60 days. Reduce DAP by 15%.) Tj
0 -40 Td
(Certified Signature: Dr. Anand Patil, Chief Agricultural Chemist) Tj
ET
endstream
endobj
xref
0 7
0000000000 65535 f 
0000000009 00000 n 
0000000122 00000 n 
0000000173 00000 n 
0000000230 00000 n 
0000000350 00000 n 
0000000430 00000 n 
trailer
<< /Size 7
   /Root 2 0 R >>
startxref
1100
%%EOF`;
    return new Blob([sampleContent], { type: 'application/pdf' });
  }
};

const API = {
  getBaseUrl() {
    if (typeof CONFIG !== 'undefined' && CONFIG.API_BASE_URL) {
      return CONFIG.API_BASE_URL;
    }
    return 'http://127.0.0.1:5000';
  },

  /**
   * Generic request wrapper
   */
  async request(endpoint, options = {}) {
    const url = `${this.getBaseUrl()}${endpoint}`;
    const headers = {
      ...(options.headers || {})
    };

    const method = (options.method || 'GET').toUpperCase();
    if (options.body || ['POST', 'PUT', 'PATCH'].includes(method)) {
      if (!headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
      }
    }

    if (typeof Auth !== 'undefined' && Auth.getToken() && !options.skipAuth) {
      headers['Authorization'] = `Bearer ${Auth.getToken()}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers
      });

      if (response.status === 401 && !options.skipAuth) {
        if (typeof Auth !== 'undefined') {
          Auth.clearSession();
          if (typeof window !== 'undefined' && !window.location.pathname.endsWith('login.html')) {
            window.location.href = 'login.html?session_expired=1';
          }
        }
        return { ok: false, status: 401, error: 'Your session has expired. Please sign in again.' };
      }

      if (options.responseType === 'blob') {
        if (!response.ok) {
          return { ok: false, status: response.status, error: 'Could not download report file.' };
        }
        const blob = await response.blob();
        return { ok: true, data: blob };
      }

      let data = {};
      try {
        data = await response.json();
      } catch (err) {
        data = {};
      }

      if (!response.ok) {
        return {
          ok: false,
          status: response.status,
          error: data.message || data.error || `Server returned error status ${response.status}`
        };
      }

      return { ok: true, status: response.status, data };
    } catch (networkError) {
      return {
        ok: false,
        offline: true,
        error: `Notice: Backend server is offline at ${this.getBaseUrl()}. Please ensure Person 1's Flask backend is running.`
      };
    }
  },

  // 1. Farmer Registration
  async farmerRegister({ name, phone, password }) {
    const res = await this.request('/api/farmer/register', {
      method: 'POST',
      skipAuth: true,
      body: JSON.stringify({ name, phone, password })
    });
    // Fallback in demo sandbox
    if (res.offline) {
      return { ok: true, offlineDemo: true, message: 'Farmer registered in preview mode.' };
    }
    return res;
  },

  // 2. Farmer Login
  async farmerLogin({ phone, password }) {
    const res = await this.request('/api/farmer/login', {
      method: 'POST',
      skipAuth: true,
      body: JSON.stringify({ phone, password })
    });
    // Fallback in demo sandbox: allow valid 10-digit number
    if (res.offline) {
      return {
        ok: true,
        offlineDemo: true,
        data: {
          token: 'demo-farmer-token',
          farmer: { id: 1, name: 'Ramesh Patil', phone: phone || '9876543210' }
        }
      };
    }
    return res;
  },

  // 3. Request / Book Soil Test Appointment
  async createAppointment({ land_details, address, preferred_date, preferred_time, notes }) {
    const res = await this.request('/api/appointments', {
      method: 'POST',
      body: JSON.stringify({ land_details, address, preferred_date, preferred_time, notes: notes || '' })
    });
    if (res.offline) {
      const created = DemoStore.addAppointment({ land_details, address, preferred_date, preferred_time, notes });
      return { ok: true, offlineDemo: true, data: { appointment: created } };
    }
    return res;
  },

  // 4. Fetch Appointments for the logged-in Farmer
  async getFarmerAppointments() {
    const res = await this.request('/api/farmer/appointments', { method: 'GET' });
    if (res.offline) {
      return {
        ok: true,
        offlineDemo: true,
        data: { appointments: DemoStore.getAppointments() }
      };
    }
    return res;
  },

  // 5. Fetch Soil Health Reports for the logged-in Farmer
  async getFarmerReports() {
    const res = await this.request('/api/farmer/reports', { method: 'GET' });
    if (res.offline) {
      return {
        ok: true,
        offlineDemo: true,
        data: { reports: DemoStore.getReports() }
      };
    }
    return res;
  },

  // 6. Download PDF Report Blob securely
  async downloadReport(reportId) {
    const res = await this.request(`/api/reports/${reportId}/download`, {
      method: 'GET',
      responseType: 'blob'
    });
    if (res.offline) {
      return { ok: true, offlineDemo: true, data: DemoStore.generateSamplePdfBlob(reportId) };
    }
    return res;
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { API, DemoStore };
}
if (typeof window !== 'undefined') {
  window.API = API;
  window.DemoStore = DemoStore;
}
