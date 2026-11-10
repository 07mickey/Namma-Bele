# Farmer Frontend Design Specification
**Project**: Soil Testing Appointment & Report Access Portal  
**Role**: Person 2 — Farmer Frontend  
**Branch**: `feature/farmer-frontend`  
**Date**: 2026-11-02  
**Status**: Approved (Pending Implementation Plan)

---

## 1. Executive Summary & Intent

The Soil Testing Appointment & Report Access Portal is a community-driven platform designed to help farmers easily book soil-testing appointments and securely access their soil-test reports. 

Person 2 is exclusively responsible for the **Farmer Frontend**. The system must feel modern, elegant, and trustworthy, combining **top-notch glassmorphism** with **clarity and minimalism**, specifically optimized for accessibility on mobile devices used by rural and community farmers.

### Guiding Principles
1. **Glassmorphism + Minimalism**: Frosted glass cards (`backdrop-filter: blur()`, translucent surfaces, delicate borders, soft ambient shadows) paired with crisp typography, generous whitespace, and purposeful contrast.
2. **Farmer-Centric Usability**: Direct language, clear status explanations, large tap targets (minimum 48px), and zero cognitive overload.
3. **Strict Separation of Concerns**: No Flask routes, SQLite models, or Admin interfaces. Only pure, standard web technologies (HTML5, modern CSS3, Vanilla ES6+ JavaScript).
4. **Honesty Over Fake Features**: No fake backend data pretending to be live. Unreachable backend servers or missing API endpoints are handled with transparent, informative placeholder notices.
5. **Security First**: Client-side authentication tokens (`Bearer <token>`) passed with all private data requests, ensuring a farmer only requests their own appointments and reports.

---

## 2. UI/UX & Glassmorphism Design System

### 2.1 Color Palette & Theme Tokens
* **Background Canvas**: Soft organic gradient mesh:
  * Primary background: `#f3f7f4` to `#e6f0e9` with subtle ambient radial gradients in sage/emerald.
* **Glass Surfaces**:
  * Glass Card: `background: rgba(255, 255, 255, 0.72); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.65); box-shadow: 0 8px 32px 0 rgba(31, 56, 38, 0.08);`
  * Glass Card (Hover/Active): `background: rgba(255, 255, 255, 0.85); box-shadow: 0 12px 40px 0 rgba(31, 56, 38, 0.12);`
  * Glass Header/Nav: `background: rgba(255, 255, 255, 0.80); backdrop-filter: blur(12px); border-bottom: 1px solid rgba(255, 255, 255, 0.5);`
* **Brand Accents**:
  * Primary Green: `#1e7e48` (Vibrant Agriculture Emerald)
  * Primary Hover: `#155d34`
  * Text Primary: `#18271e` (Deep forest slate for maximum readability)
  * Text Muted: `#506859`
* **Agreed Status Tokens**:
  * `Pending`: Background `rgba(245, 158, 11, 0.15)`, Border `rgba(245, 158, 11, 0.4)`, Text `#b45309` (Amber)
  * `Approved`: Background `rgba(2, 132, 199, 0.15)`, Border `rgba(2, 132, 199, 0.4)`, Text `#0369a1` (Sky/Blue)
  * `Rejected`: Background `rgba(225, 29, 72, 0.15)`, Border `rgba(225, 29, 72, 0.4)`, Text `#be123c` (Crimson)
  * `Completed`: Background `rgba(22, 163, 74, 0.15)`, Border `rgba(22, 163, 74, 0.4)`, Text `#15803d` (Green)

### 2.2 Typography & Elements
* **Typography Stack**: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`
* **Form Inputs**:
  * Large, comfortable inputs (min height 48px, font-size 16px to prevent iOS auto-zoom).
  * Frosted white background with focused glowing green ring (`outline: none; box-shadow: 0 0 0 3px rgba(30, 126, 72, 0.25)`).
* **Buttons**:
  * Primary: Solid emerald gradient with soft elevation.
  * Secondary / Glass: Frosted translucent button with subtle border.

---

## 3. Architecture & File Structure

```text
soilfrontend/
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-11-02-farmer-frontend-design.md
├── index.html              # Home page: intro, value prop, 4-step workflow, login/register CTAs
├── register.html           # Farmer registration form with instant validation
├── login.html              # Farmer login with phone & password
├── dashboard.html          # Farmer dashboard (welcome banner, active status, quick links, logout)
├── book-appointment.html   # Soil test booking form (field details, address, date/time, notes)
├── appointments.html       # My Appointments (status list with badges & live filtering)
├── reports.html            # My Reports (secure list of completed PDF reports for download)
├── css/
│   └── styles.css          # Unified glassmorphism + minimalist responsive CSS
├── js/
│   ├── config.js           # API base URL configuration (default http://127.0.0.1:5000)
│   ├── api.js              # Centralized fetch client (headers, Bearer tokens, error normalization)
│   ├── auth.js             # Farmer session management (session storage, login redirect, route protection)
│   ├── validation.js       # Client validation logic (10-digit phone, password matching, required fields)
│   ├── appointments.js     # Form submission for booking and rendering appointments list
│   └── reports.js          # Fetching and downloading farmer reports
└── README.md               # How to run, API contract for Person 1, and verification notes
```

---

## 4. Page-by-Page Specifications

### 4.1 Home Page (`index.html`)
* **Navigation Bar**: Glassmorphic sticky header with logo ("🌱 SoilTest Portal") and navigation items (`Home`, `How It Works`, `Login`, `Register`).
* **Hero Section**:
  * Heading: "Know Your Soil. Harvest Better Yields."
  * Subtext: "A simple, community-first portal for local farmers to request soil health testing and access official test reports online."
  * Action Buttons: `[Request a Soil Test]` (navigates to login or booking if logged in) and `[Farmer Login]`.
* **Why Test Your Soil (3 Minimal Glass Cards)**:
  1. *Save Fertilizer Costs*: Apply only what your field truly lacks.
  2. *Optimize Soil pH & Nutrients*: Maintain long-term soil health and moisture retention.
  3. *Increase Crop Yield*: Harvest stronger crops with lab-verified recommendations.
* **How It Works (4 Clean Visual Steps)**:
  1. **Register**: Create your account using your mobile phone number.
  2. **Request Test**: Enter your farm location and select a preferred appointment date.
  3. **Sample Testing**: An approved coordinator collects the soil sample for lab analysis.
  4. **Get Report**: View and download your official soil test PDF report anytime.
* **Footer**: Simple, elegant community disclaimer and contact assistance info.

### 4.2 Farmer Registration (`register.html`)
* **Glass Container**: Centered minimalist card.
* **Fields**:
  * Full Name (text, required)
  * Phone Number (tel, 10-digit numeric constraint, required)
  * Password (password, min 6 chars, required)
  * Confirm Password (password, required)
* **Client Validation**:
  * Real-time validation badges (checks phone length, flags password mismatches before submission).
* **Submission**:
  * Sends payload to `POST /api/farmer/register`.
  * If backend is not running: displays a clear, elegant alert banner:
    `[Notice: Backend server offline. Please ensure Person 1's Flask backend is running on http://127.0.0.1:5000]`.
  * On success: stores notification and redirects to `login.html?registered=true`.

### 4.3 Farmer Login (`login.html`)
* **Glass Container**: Centered minimalist card.
* **Fields**:
  * Phone Number (tel, required)
  * Password (password, required)
* **Error Banner Area**: Dedicated glass alert container for showing authentication errors or backend connectivity messages.
* **Submission**:
  * Calls `POST /api/farmer/login`.
  * On success: saves auth token and farmer details (`id`, `name`, `phone`) to browser storage, redirects to `dashboard.html`.

### 4.4 Farmer Dashboard (`dashboard.html`)
* **Route Protection**: If unauthenticated, immediately redirects to `login.html`.
* **Header / Greeting**: "Welcome back, **[Farmer Name]** (📱 [Phone])" + `[Logout]` button.
* **Current Appointment Status Banner (Glass Card)**:
  * Pulls the most recent appointment for the farmer.
  * Prominently displays current status badge (`Pending`, `Approved`, `Rejected`, `Completed`).
  * Displays friendly explanation:
    * *Pending*: "Your appointment request has been received and is waiting for coordinator review."
    * *Approved*: "Your request is approved! A field coordinator will visit on your scheduled date."
    * *Rejected*: "Your request was declined. Please view appointment details or request a new slot."
    * *Completed*: "Soil analysis complete! Your official PDF report is available in My Reports."
  * If no appointments exist: "No active appointment. Request your first soil test below."
* **Action Grid (3 Minimalist Frosted Cards)**:
  1. 🌾 **Book Soil Test**: Jump straight to booking form.
  2. 📅 **My Appointments**: View status and history of all appointments.
  3. 📄 **My Reports**: Access and download verified PDF reports.

### 4.5 Book Soil Test (`book-appointment.html`)
* **Route Protection**: Requires authenticated session.
* **Fields**:
  * Land / Field Identification (e.g., "Survey No. 104, North Plot - 3.5 Acres")
  * Field Location / Address (Village, Landmark, Taluk/District)
  * Preferred Date (HTML5 date picker, restricted to tomorrow onwards)
  * Preferred Time Slot (`Morning (8:00 AM - 12:00 PM)` or `Afternoon (1:00 PM - 5:00 PM)`)
  * Additional Notes (Optional: previous crop, fertilizer used, pest or drainage observations)
* **Submission**:
  * Sends `POST /api/appointments` with `Authorization: Bearer <token>`.
  * On success: redirects to `appointments.html` with status `Pending`.

### 4.6 My Appointments (`appointments.html`)
* **Route Protection**: Requires authenticated session.
* **Header**: "My Soil Testing Appointments" + `[+ Book New Test]` button.
* **List Display**:
  * Clean frosted glass cards for each appointment.
  * Information displayed:
    * Reference / Appointment ID
    * Land Details & Address
    * Preferred Date & Time Slot
    * Current Status Badge (`Pending`, `Approved`, `Rejected`, `Completed`)
    * If status is `Completed`: direct `[📄 Access Report]` button linking to `reports.html?appointment_id=...`.
* **Empty State**: Friendly glass banner: "You haven't requested any soil tests yet. [Book a Test Now]".
* **Offline Notice**: If backend is offline, displays a clear indicator explaining Person 1's backend service needs to be active.

### 4.7 My Reports (`reports.html`)
* **Route Protection**: Requires authenticated session.
* **Security Rule Compliance**:
  * Frontend only ever requests the logged-in farmer's reports via `GET /api/farmer/reports` using their authenticated session token.
  * No URL-based ID tampering is permitted to load reports from another farmer.
* **List Display**:
  * Card per report showing:
    * Report Date
    * Appointment Reference & Field Name
    * Status: "Lab Verified Report Available"
    * `[⬇ Download PDF Report]` button.
* **Download Handler**:
  * Calls `GET /api/reports/:id/download` with `Authorization: Bearer <token>`.
  * Opens/downloads PDF blob safely.
* **Empty State**: Glass notification card: "No test reports available yet. Once your soil sample has been tested and marked completed by the admin, your official report will appear here."

---

## 5. API Interface Contract (For Person 1)

All endpoints expect and return standard JSON, except report download which returns `application/pdf`.

| Endpoint | Method | Auth | Request Body | Response (Success 200/201) |
|---|---|---|---|---|
| `/api/farmer/register` | `POST` | None | `{ "name": "Ramesh", "phone": "9876543210", "password": "secretpassword" }` | `{ "success": true, "message": "Farmer registered successfully" }` |
| `/api/farmer/login` | `POST` | None | `{ "phone": "9876543210", "password": "secretpassword" }` | `{ "success": true, "token": "jwt_or_session_token", "farmer": { "id": 1, "name": "Ramesh", "phone": "9876543210" } }` |
| `/api/appointments` | `POST` | Bearer Token | `{ "land_details": "Plot 4B", "address": "Green Village", "preferred_date": "2026-11-10", "preferred_time": "Morning", "notes": "Cotton crop" }` | `{ "success": true, "appointment": { "id": 101, "status": "Pending", ... } }` |
| `/api/farmer/appointments` | `GET` | Bearer Token | None | `{ "success": true, "appointments": [ { "id": 101, "land_details": "Plot 4B", "address": "Green Village", "preferred_date": "2026-11-10", "preferred_time": "Morning", "status": "Pending", "created_at": "2026-11-02" } ] }` |
| `/api/farmer/reports` | `GET` | Bearer Token | None | `{ "success": true, "reports": [ { "id": 201, "appointment_id": 101, "land_details": "Plot 4B", "report_date": "2026-11-12", "file_name": "soil_report_101.pdf" } ] }` |
| `/api/reports/:id/download` | `GET` | Bearer Token | None | Binary PDF stream (`Content-Type: application/pdf`) |

---

## 6. Verification & Quality Assurance Strategy

1. **Client-Side Form Validation**:
   * Non-numeric or <10 digit phone inputs are blocked with immediate helper text.
   * Password mismatch is clearly flagged before sending network requests.
   * Dates in the past are disabled in the date selector.
2. **Session Guarding**:
   * Attempting to open `dashboard.html`, `book-appointment.html`, `appointments.html`, or `reports.html` without a stored session instantly routes to `login.html`.
   * Logout clears session storage and routes cleanly to `login.html`.
3. **Responsive Visual Testing**:
   * Tested on mobile portrait widths (360px, 390px, 412px), tablet (768px), and desktop (1200px+).
   * All glassmorphism elements maintain high legibility with backdrop filters and fallback solid fills for unsupported browsers.
4. **Backend Unavailability Handling**:
   * When `fetch()` catches `TypeError: Failed to fetch` (backend not running), the UI cleanly displays an informative notice rather than crashing or showing raw console errors.

