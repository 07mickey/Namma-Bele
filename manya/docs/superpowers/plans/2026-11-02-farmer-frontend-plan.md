# Farmer Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete, mobile-friendly, minimalist glassmorphic farmer frontend (Green, White, Earth-Brown aesthetic) for the Soil Testing Appointment & Report Access Portal.

**Architecture:** Multi-page HTML5 application styled with custom responsive CSS (frosted glass blur, emerald/loam/white tokens) and powered by vanilla ES6+ modules (`api.js`, `auth.js`, `validation.js`, `appointments.js`, `reports.js`). All dynamic data calls pass through a centralized API layer designed to interface cleanly with Person 1's Flask backend and fail gracefully with informative notices when offline.

**Tech Stack:** HTML5, Modern CSS3 (CSS Variables, Flexbox/Grid, Backdrop Filter), Vanilla ES6+ JavaScript, Node.js (for headless DOM validation tests).

**Spec:** [docs/superpowers/specs/2026-11-02-farmer-frontend-design.md](file:///Users/rahulursnr/soilfrontend/docs/superpowers/specs/2026-11-02-farmer-frontend-design.md)

## Global Constraints

- **Language / Runtime:** Pure HTML5, CSS3, Vanilla JavaScript (no external frameworks like React, Vue, or Tailwind CDN).
- **Aesthetic:** Top-notch glassmorphism + minimalism with an organic agricultural palette: emerald greens (`#1e7e48`, `#14532d`), rich loam soil browns (`#6e4726`, `#8d5b32`), and frosted crisp whites (`rgba(255, 255, 255, 0.75)`).
- **Role Boundaries (Person 2):** Strictly Farmer-facing frontend. No SQLite database, no Flask routes, no Admin interfaces.
- **Statuses Supported:** Strictly `Pending`, `Approved`, `Rejected`, `Completed`.
- **Backend Offline Handling:** When Person 1's backend is not running or unreachable, display a visible, respectful alert banner instead of crashing or showing fake data.
- **Git Branch:** All work committed to branch `feature/farmer-frontend` with concise, meaningful commit messages.

## Review Focus

1. **Unreachable Backend:** When `fetch()` fails because Person 1's Flask server is offline, forms and dashboard displays must gracefully show `[Notice: Backend server offline at http://127.0.0.1:5000]` rather than breaking silently.
2. **Invalid Phone Input:** Phone input must strictly enforce 10 numeric digits; non-numeric characters or incorrect lengths must display clear inline validation errors before sending network requests.
3. **Password Mismatch:** Registration form must catch mismatched passwords immediately with user-friendly red/amber feedback before form submit.
4. **Session Guarding & ID Tampering:** Visiting protected pages (`dashboard.html`, `book-appointment.html`, `appointments.html`, `reports.html`) while logged out must immediately redirect to `login.html`. Report access must use the logged-in session token, never exposing a URL query parameter that could leak another farmer's report.
5. **Past Date Selection in Booking:** Preferred appointment date must not allow dates in the past or today (minimum date = tomorrow).

---

### Task 1: Design System & Styling (Green, White, Brown Glassmorphism, Responsive CSS)

**Files:**
- Create: `css/styles.css`
- Test: `tests/test_css_tokens.js`

**Interfaces:**
- Produces: CSS custom properties (`--color-green-primary`, `--color-earth-brown`, `--glass-bg`, `--status-pending`, etc.), utility classes (`.glass-card`, `.glass-nav`, `.btn-primary`, `.status-badge`), and responsive breakpoints (mobile `<=640px`, tablet `<=960px`, desktop `>960px`).

- [ ] **Step 1: Write verification test for CSS tokens and rules**

```javascript
// tests/test_css_tokens.js
const fs = require('fs');
const assert = require('assert');

const css = fs.readFileSync('css/styles.css', 'utf8');

// Check required color palette tokens: Green, White, Earth Brown
assert(css.includes('--color-primary-green'), 'Missing --color-primary-green');
assert(css.includes('--color-earth-brown'), 'Missing --color-earth-brown');
assert(css.includes('--glass-bg'), 'Missing --glass-bg');

// Check status badges
assert(css.includes('.status-pending'), 'Missing .status-pending');
assert(css.includes('.status-approved'), 'Missing .status-approved');
assert(css.includes('.status-rejected'), 'Missing .status-rejected');
assert(css.includes('.status-completed'), 'Missing .status-completed');

// Check backdrop-filter
assert(css.includes('backdrop-filter'), 'Missing backdrop-filter for glassmorphism');
console.log('CSS tokens and rules verified successfully.');
```

- [ ] **Step 2: Run test to verify it fails before file creation**

Run: `node tests/test_css_tokens.js`  
Expected: Error: ENOENT: no such file or directory, open 'css/styles.css'

- [ ] **Step 3: Implement `css/styles.css`**

Implement comprehensive glassmorphic stylesheet with:
- Variables: Green (`#1e7e48`, `#14532d`, `#e8f5e9`), Earth Brown (`#6e4726`, `#8d5b32`, `#fdfaf6`), Crisp White Frosted Glass (`rgba(255, 255, 255, 0.72)`).
- Ambient organic radial background gradient.
- Glass components: `.glass-card`, `.glass-nav`, `.glass-header`, `.glass-footer`, `.glass-alert`.
- Status badges: `.status-pending` (amber), `.status-approved` (sky/blue), `.status-rejected` (crimson), `.status-completed` (emerald).
- Mobile-first responsive grid and media queries (touch targets >= 48px, minimum font-size 16px).

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/test_css_tokens.js`  
Expected: "CSS tokens and rules verified successfully."

- [ ] **Step 5: Commit**

```bash
git add css/styles.css tests/test_css_tokens.js
git commit -m "feat: add green white brown glassmorphism responsive design system"
```

---

### Task 2: Core JavaScript Modules (Config, API Client, Auth State, Validation)

**Files:**
- Create: `js/config.js`
- Create: `js/api.js`
- Create: `js/auth.js`
- Create: `js/validation.js`
- Test: `tests/test_core_js.js`

**Interfaces:**
- `config.js`: Exports `CONFIG = { API_BASE_URL: 'http://127.0.0.1:5000' }`
- `validation.js`:
  - `validatePhone(phone: string): { isValid: boolean, error: string }`
  - `validatePassword(password: string): { isValid: boolean, error: string }`
  - `validatePasswordMatch(pwd: string, confirm: string): { isValid: boolean, error: string }`
- `auth.js`:
  - `saveSession(token: string, farmer: { id, name, phone }): void`
  - `getSession(): { token, farmer } | null`
  - `clearSession(): void`
  - `requireAuth(): boolean` (redirects to login.html if not authenticated)
- `api.js`:
  - `apiRequest(endpoint: string, options: object): Promise<{ ok: boolean, data?: any, error?: string, offline?: boolean }>`

- [ ] **Step 1: Write test for validation and session logic**

```javascript
// tests/test_core_js.js
const assert = require('assert');
const { validatePhone, validatePassword, validatePasswordMatch } = require('../js/validation.js');

// Phone tests
assert.strictEqual(validatePhone('9876543210').isValid, true);
assert.strictEqual(validatePhone('12345').isValid, false);
assert.strictEqual(validatePhone('98765abcde').isValid, false);

// Password tests
assert.strictEqual(validatePassword('123456').isValid, true);
assert.strictEqual(validatePassword('123').isValid, false);
assert.strictEqual(validatePasswordMatch('secret1', 'secret1').isValid, true);
assert.strictEqual(validatePasswordMatch('secret1', 'secret2').isValid, false);

console.log('Core JS validation tests passed.');
```

- [ ] **Step 2: Run test to verify it fails before implementation**

Run: `node tests/test_core_js.js`  
Expected: Cannot find module '../js/validation.js'

- [ ] **Step 3: Implement `js/config.js`, `js/validation.js`, `js/auth.js`, and `js/api.js`**

Implement:
- `js/config.js`: Default API host `http://127.0.0.1:5000`.
- `js/validation.js`: Universal CommonJS + browser compatibility (`if (typeof module !== 'undefined') module.exports = ...`).
- `js/auth.js`: Local storage session helper with automatic login redirect on protected views and user greeting helpers.
- `js/api.js`: Centralized fetch wrapper that catches network errors (`TypeError: Failed to fetch`) and returns `{ ok: false, offline: true, error: "Backend server is currently offline..." }`.

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/test_core_js.js`  
Expected: "Core JS validation tests passed."

- [ ] **Step 5: Commit**

```bash
git add js/config.js js/validation.js js/auth.js js/api.js tests/test_core_js.js
git commit -m "feat: add api client, auth session manager, and client validation modules"
```

---

### Task 3: Home Page (`index.html`)

**Files:**
- Create: `index.html`
- Test: `tests/test_home_page.js`

**Interfaces:**
- Consumes: `css/styles.css`, `js/auth.js`
- Produces: Visual introduction, 3 value proposition cards, 4-step process guide, dynamic login/dashboard navbar state, CTA buttons.

- [ ] **Step 1: Write test for home page structure**

```javascript
// tests/test_home_page.js
const fs = require('fs');
const assert = require('assert');

const html = fs.readFileSync('index.html', 'utf8');

assert(html.includes('Soil Testing Appointment & Report Access Portal'), 'Missing portal title');
assert(html.includes('How It Works') || html.includes('Process'), 'Missing How it works');
assert(html.includes('login.html'), 'Missing login link');
assert(html.includes('register.html'), 'Missing register link');
assert(html.includes('book-appointment.html'), 'Missing book appointment link');
console.log('Home page structure verified.');
```

- [ ] **Step 2: Run test to verify failure**

Run: `node tests/test_home_page.js`  
Expected: ENOENT: no such file or directory, open 'index.html'

- [ ] **Step 3: Implement `index.html`**

Build:
- Glassmorphic navigation header with soil leaf icon and responsive links.
- Hero banner with headline, introductory description, and action buttons (`Book Soil Test` and `Farmer Login`).
- "Why Test Soil?" cards: Save Fertilizer Costs, Optimize Nutrients & pH, Increase Crop Yield.
- "4-Step Process Guide": Register -> Request Test -> Sample Testing -> Get Report.
- Community footer with helpline support text.
- Script snippet updating the navbar dynamically if the farmer is already logged in (shows "Go to Dashboard" and "Logout").

- [ ] **Step 4: Run test to verify passes**

Run: `node tests/test_home_page.js`  
Expected: "Home page structure verified."

- [ ] **Step 5: Commit**

```bash
git add index.html tests/test_home_page.js
git commit -m "feat: add farmer home page with process guide and value cards"
```

---

### Task 4: Farmer Authentication Views (`register.html` & `login.html`)

**Files:**
- Create: `register.html`
- Create: `login.html`
- Test: `tests/test_auth_pages.js`

**Interfaces:**
- Consumes: `css/styles.css`, `js/config.js`, `js/validation.js`, `js/api.js`, `js/auth.js`
- Produces: Complete user registration & login forms with real-time feedback, API dispatch, offline alerts, and session storage.

- [ ] **Step 1: Write test for registration and login pages markup**

```javascript
// tests/test_auth_pages.js
const fs = require('fs');
const assert = require('assert');

const regHtml = fs.readFileSync('register.html', 'utf8');
assert(regHtml.includes('name="name"'), 'Registration missing name field');
assert(regHtml.includes('name="phone"'), 'Registration missing phone field');
assert(regHtml.includes('name="password"'), 'Registration missing password field');
assert(regHtml.includes('name="confirm_password"'), 'Registration missing confirm password field');

const loginHtml = fs.readFileSync('login.html', 'utf8');
assert(loginHtml.includes('name="phone"'), 'Login missing phone field');
assert(loginHtml.includes('name="password"'), 'Login missing password field');
assert(loginHtml.includes('error-banner') || loginHtml.includes('alert'), 'Login missing error message area');

console.log('Auth pages markup verified.');
```

- [ ] **Step 2: Run test to verify failure**

Run: `node tests/test_auth_pages.js`  
Expected: ENOENT: no such file or directory, open 'register.html'

- [ ] **Step 3: Implement `register.html` and `login.html`**

Build:
- `register.html`:
  - Centered frosted glass container with organic green/brown accents.
  - Inputs: Name, Phone (with 10-digit helper), Password, Confirm Password.
  - Real-time client-side validation triggers on input blur/typing.
  - Submits to `api.farmerRegister({ name, phone, password })`.
  - Handles offline state by displaying: `[Notice: Backend server offline. Please ensure Person 1's Flask backend is running on http://127.0.0.1:5000]`.
  - Redirects to `login.html?registered=1` on success.
- `login.html`:
  - Centered frosted glass container.
  - Inputs: Phone number and Password.
  - Error banner area for invalid credentials or connection issues.
  - Submits to `api.farmerLogin({ phone, password })`.
  - Stores token and farmer profile in `sessionStorage` and routes to `dashboard.html`.

- [ ] **Step 4: Run test to verify passes**

Run: `node tests/test_auth_pages.js`  
Expected: "Auth pages markup verified."

- [ ] **Step 5: Commit**

```bash
git add register.html login.html tests/test_auth_pages.js
git commit -m "feat: add farmer registration and login pages with live validation"
```

---

### Task 5: Farmer Dashboard (`dashboard.html`)

**Files:**
- Create: `dashboard.html`
- Test: `tests/test_dashboard_page.js`

**Interfaces:**
- Consumes: `css/styles.css`, `js/config.js`, `js/auth.js`, `js/api.js`
- Produces: Protected dashboard displaying farmer name, latest appointment status banner (`Pending`/`Approved`/`Rejected`/`Completed`), quick navigation cards, and logout.

- [ ] **Step 1: Write test for dashboard structure**

```javascript
// tests/test_dashboard_page.js
const fs = require('fs');
const assert = require('assert');

const html = fs.readFileSync('dashboard.html', 'utf8');
assert(html.includes('farmer-name') || html.includes('Welcome'), 'Missing farmer greeting');
assert(html.includes('latest-status') || html.includes('appointment-status'), 'Missing status card');
assert(html.includes('book-appointment.html'), 'Missing book test link');
assert(html.includes('appointments.html'), 'Missing appointments link');
assert(html.includes('reports.html'), 'Missing reports link');
assert(html.includes('logout'), 'Missing logout option');
console.log('Dashboard structure verified.');
```

- [ ] **Step 2: Run test to verify failure**

Run: `node tests/test_dashboard_page.js`  
Expected: ENOENT: no such file or directory, open 'dashboard.html'

- [ ] **Step 3: Implement `dashboard.html`**

Build:
- Immediate auth check script (calls `Auth.requireAuth()`).
- Farmer greeting header: shows farmer's name and phone number.
- Latest appointment status card:
  - Fetches latest appointment from `api.getFarmerAppointments()`.
  - Renders status pill with agreed tokens: `Pending`, `Approved`, `Rejected`, `Completed`.
  - Displays plain-language guidance based on the status.
  - If offline: displays friendly notice indicating Person 1's backend is not yet connected.
- 3 Quick Action Glass Cards:
  - 🌾 **Book Soil Test**: Navigate to `book-appointment.html`.
  - 📅 **My Appointments**: Navigate to `appointments.html`.
  - 📄 **My Reports**: Navigate to `reports.html`.
- Logout button with session clearance.

- [ ] **Step 4: Run test to verify passes**

Run: `node tests/test_dashboard_page.js`  
Expected: "Dashboard structure verified."

- [ ] **Step 5: Commit**

```bash
git add dashboard.html tests/test_dashboard_page.js
git commit -m "feat: add farmer dashboard with active appointment status card"
```

---

### Task 6: Book Soil Test View (`book-appointment.html` & `js/appointments.js`)

**Files:**
- Create: `book-appointment.html`
- Create: `js/appointments.js`
- Test: `tests/test_booking_page.js`

**Interfaces:**
- Consumes: `css/styles.css`, `js/config.js`, `js/auth.js`, `js/api.js`
- Produces: Soil test booking form with fields (land details, address, preferred date min=tomorrow, time slot, notes) and API submission handler.

- [ ] **Step 1: Write test for booking form elements**

```javascript
// tests/test_booking_page.js
const fs = require('fs');
const assert = require('assert');

const html = fs.readFileSync('book-appointment.html', 'utf8');
assert(html.includes('name="land_details"'), 'Missing land_details field');
assert(html.includes('name="address"'), 'Missing address field');
assert(html.includes('name="preferred_date"'), 'Missing preferred_date field');
assert(html.includes('name="preferred_time"'), 'Missing preferred_time field');
assert(html.includes('name="notes"'), 'Missing notes field');
console.log('Booking page elements verified.');
```

- [ ] **Step 2: Run test to verify failure**

Run: `node tests/test_booking_page.js`  
Expected: ENOENT: no such file or directory, open 'book-appointment.html'

- [ ] **Step 3: Implement `book-appointment.html` and `js/appointments.js`**

Build:
- Form fields:
  - Land Details (e.g., "Survey No. 42, North Acre")
  - Address / Village (e.g., "Near Primary School, Someshwar Village")
  - Preferred Date (Date picker with JS setting `min` attribute to tomorrow's date)
  - Preferred Time Slot (Morning: 8:00 AM - 12:00 PM, Afternoon: 1:00 PM - 5:00 PM)
  - Notes / Crop details (Optional)
- `js/appointments.js`:
  - Enforces date validation (rejects past or today).
  - Handles submission to `api.createAppointment(...)`.
  - Shows success modal / banner and redirects to `appointments.html` with status badge `Pending`.
  - If offline: displays clearly marked placeholder status alert.

- [ ] **Step 4: Run test to verify passes**

Run: `node tests/test_booking_page.js`  
Expected: "Booking page elements verified."

- [ ] **Step 5: Commit**

```bash
git add book-appointment.html js/appointments.js tests/test_booking_page.js
git commit -m "feat: add soil test booking form and appointments handler"
```

---

### Task 7: My Appointments & My Reports Views (`appointments.html`, `reports.html`, `js/reports.js`)

**Files:**
- Create: `appointments.html`
- Create: `reports.html`
- Create: `js/reports.js`
- Test: `tests/test_appointments_and_reports.js`

**Interfaces:**
- Consumes: `css/styles.css`, `js/config.js`, `js/auth.js`, `js/api.js`
- Produces: List of appointments with status tags, list of verified reports, direct PDF download trigger, and empty states.

- [ ] **Step 1: Write test for appointments and reports markup**

```javascript
// tests/test_appointments_and_reports.js
const fs = require('fs');
const assert = require('assert');

const aptHtml = fs.readFileSync('appointments.html', 'utf8');
assert(aptHtml.includes('appointments-list') || aptHtml.includes('appointment-card'), 'Missing appointments container');
assert(aptHtml.includes('Pending') || aptHtml.includes('status'), 'Missing status references');

const repHtml = fs.readFileSync('reports.html', 'utf8');
assert(repHtml.includes('reports-list') || repHtml.includes('report-card'), 'Missing reports container');
assert(repHtml.includes('download') || repHtml.includes('Download'), 'Missing download option');

console.log('Appointments and reports markup verified.');
```

- [ ] **Step 2: Run test to verify failure**

Run: `node tests/test_appointments_and_reports.js`  
Expected: ENOENT: no such file or directory, open 'appointments.html'

- [ ] **Step 3: Implement `appointments.html`, `reports.html`, and `js/reports.js`**

Build:
- `appointments.html`:
  - Clean card listing for appointments.
  - Filter tabs: All, Pending, Approved, Completed, Rejected.
  - Badges using agreed colors.
  - Link to "View Report" when status is `Completed`.
  - Empty state when no appointments exist.
- `reports.html`:
  - List of soil test reports belonging strictly to the logged-in farmer.
  - Displays Report Date, Appointment Reference, Field Name, and `[⬇ Download PDF Report]` button.
  - Empty state when no reports are available yet.
- `js/reports.js`:
  - Fetches reports via `api.getFarmerReports()`.
  - PDF download handler calling `api.downloadReport(reportId)` with bearer token.
  - If backend is offline: displays friendly indicator.

- [ ] **Step 4: Run test to verify passes**

Run: `node tests/test_appointments_and_reports.js`  
Expected: "Appointments and reports markup verified."

- [ ] **Step 5: Commit**

```bash
git add appointments.html reports.html js/reports.js tests/test_appointments_and_reports.js
git commit -m "feat: add appointments listing and secure reports view with PDF download"
```

---

### Task 8: Verification, Documentation, and Final Deliverable Report

**Files:**
- Create: `README.md`
- Create: `tests/run_all_tests.sh`
- Test: `tests/run_all_tests.sh`

**Interfaces:**
- Produces: Project documentation, API contract guide for Person 1, how to run instructions, and complete test runner.

- [ ] **Step 1: Write test runner script**

```bash
# tests/run_all_tests.sh
set -e
echo "Running Farmer Frontend verification suite..."
node tests/test_css_tokens.js
node tests/test_core_js.js
node tests/test_home_page.js
node tests/test_auth_pages.js
node tests/test_dashboard_page.js
node tests/test_booking_page.js
node tests/test_appointments_and_reports.js
echo "All tests passed successfully!"
```

- [ ] **Step 2: Implement `README.md`**

Include:
- Project Overview & Role of Person 2.
- UI/UX Design System (Green, White, Earth-Brown Glassmorphism + Minimalism).
- Exact Backend API Contract required by Person 1.
- Instructions on how to preview and test the frontend (e.g. `python3 -m http.server 3000`).
- Status of placeholders when waiting for Person 1's backend.

- [ ] **Step 3: Run the complete test suite**

Run: `bash tests/run_all_tests.sh`  
Expected: "All tests passed successfully!"

- [ ] **Step 4: Commit**

```bash
git add README.md tests/run_all_tests.sh
git commit -m "docs: add project documentation, run instructions, and test runner"
```

---

## Self-Review Against Spec

1. **Spec coverage:** All 7 pages (Home, Register, Login, Dashboard, Booking, Appointments, Reports) are accounted for. The 4 approved statuses (`Pending`, `Approved`, `Rejected`, `Completed`) and green/white/brown glassmorphic tokens are explicitly tested.
2. **Step scan:** Each task carries exact file paths, explicit test code, exact commands, and atomic git commits.
3. **Type/signature consistency:** Validation functions, session methods, and API signatures match across tasks.
4. **Review focus coverage:** Unreachable backend, phone validation, password matching, session guarding, and future-date validation are directly enforced.
5. **Proportion:** The plan is focused and actionable without bloated transcripts.

