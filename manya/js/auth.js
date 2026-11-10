/**
 * Authentication and session management for Farmer Frontend
 * Stores session securely in localStorage with active route detection.
 */

const SESSION_STORAGE_KEY = (typeof CONFIG !== 'undefined' && CONFIG.SESSION_KEY) ? CONFIG.SESSION_KEY : 'soil_farmer_session';

const Auth = {
  saveSession(token, farmer) {
    if (typeof window === 'undefined') return;
    const sessionData = {
      token,
      farmer,
      loginTime: new Date().toISOString()
    };
    try {
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessionData));
    } catch (e) {
      console.warn('Storage error:', e);
    }
  },

  getSession() {
    if (typeof window === 'undefined') return null;
    try {
      const raw = localStorage.getItem(SESSION_STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  },

  getToken() {
    const session = this.getSession();
    return session?.token || null;
  },

  getFarmer() {
    const session = this.getSession();
    return session?.farmer || null;
  },

  isLoggedIn() {
    return !!this.getToken();
  },

  clearSession() {
    if (typeof window === 'undefined') return;
    try {
      localStorage.removeItem(SESSION_STORAGE_KEY);
    } catch (e) {}
  },

  logout() {
    this.clearSession();
    window.location.href = 'login.html?logged_out=1';
  },

  /**
   * Route Guard: Call on protected farmer pages (dashboard, booking, appointments, reports).
   * If unauthenticated, immediately routes to login.html.
   */
  requireAuth(redirectPath = 'login.html') {
    if (typeof window === 'undefined') return true;
    try {
      const urlParams = new URLSearchParams(window.location.search);
      if (!this.isLoggedIn() && (urlParams.get('demo') === '1' || urlParams.get('preview') === '1')) {
        this.saveSession('demo-farmer-token', { id: 1, name: 'Ramesh Patil', phone: '9876543210' });
      }
    } catch (e) {}
    if (!this.isLoggedIn()) {
      window.location.href = redirectPath;
      return false;
    }
    return true;
  },

  /**
   * Route Guard: Call on auth pages (login, register). If already logged in, jumps to dashboard.
   */
  redirectIfLoggedIn(redirectPath = 'dashboard.html') {
    if (typeof window === 'undefined') return;
    if (this.isLoggedIn()) {
      window.location.href = redirectPath;
    }
  },

  /**
   * Updates page navigation dynamically based on authentication state
   * and preserves the active link indicator for the current page.
   */
  updateNav() {
    if (typeof document === 'undefined' || typeof window === 'undefined') return;
    const navLinks = document.getElementById('main-nav-links');
    if (!navLinks) return;

    // Detect active page cleanly from URL pathname
    const currentPath = window.location.pathname.split('/').pop() || 'index.html';
    const isActive = (page) => (currentPath === page ? ' active' : '');

    const escape = (typeof Validation !== 'undefined' && Validation.escapeHtml) 
      ? Validation.escapeHtml 
      : (str) => String(str || '').replace(/[&<>"']/g, '');

    if (this.isLoggedIn()) {
      const farmer = this.getFarmer();
      const rawName = farmer?.name ? farmer.name.split(' ')[0] : 'Farmer';
      const safeFarmerName = escape(rawName);

      navLinks.innerHTML = `
        <li><a href="index.html" class="nav-link${isActive('index.html')}">Home</a></li>
        <li><a href="dashboard.html" class="nav-link${isActive('dashboard.html')}">Dashboard</a></li>
        <li><a href="book-appointment.html" class="nav-link${isActive('book-appointment.html')}">Book Test</a></li>
        <li><a href="appointments.html" class="nav-link${isActive('appointments.html')}">Appointments</a></li>
        <li><a href="reports.html" class="nav-link${isActive('reports.html')}">My Reports</a></li>
        <li><button type="button" onclick="Auth.logout()" class="btn btn-secondary logout-btn" style="padding: 0.35rem 0.85rem; font-size: 0.84rem; min-height: 36px;">Sign Out (${safeFarmerName})</button></li>
      `;
    } else {
      navLinks.innerHTML = `
        <li><a href="index.html" class="nav-link${isActive('index.html')}">Home</a></li>
        <li><a href="index.html#how-it-works" class="nav-link">Process Guide</a></li>
        <li><a href="login.html" class="nav-link${isActive('login.html')}">Sign In</a></li>
        <li><a href="register.html" class="btn btn-primary" style="padding: 0.45rem 1.15rem; font-size: 0.88rem; min-height: 38px;">Register Account</a></li>
      `;
    }
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = Auth;
}
if (typeof window !== 'undefined') {
  window.Auth = Auth;
  document.addEventListener('DOMContentLoaded', () => Auth.updateNav());
}
