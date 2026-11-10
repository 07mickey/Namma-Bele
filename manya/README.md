# Soil Testing Appointment & Report Access Portal
## Complete UI/UX Portal Suite (Farmer & Administrator)

A simple, community-focused web portal designed to help local farmers easily request soil-testing appointments and securely access their verified laboratory test reports, coupled with a coordinator administrative console to approve visits and publish reports.

Built with **HTML5, Modern CSS3, and Vanilla JavaScript** on branch `feature/farmer-frontend`.

---

## 🎨 Design System: Top-Notch Minimalist Glassmorphism

- **Agricultural Color Harmony**:
  - **Vibrant Agricultural Green** (`#1e7e48`, `#155d34`): Foliage health and vitality.
  - **Rich Earth Loam Brown** (`#6e4726`, `#8d5b32`): Fertile soil and furrow tones.
  - **Frosted Crisp White Glass** (`rgba(255, 255, 255, 0.76)`): High-contrast minimalist cards with `backdrop-filter: blur(16px)`.
- **Accessibility**:
  - Minimum 48px touch targets for effortless field and mobile usage.
  - High-contrast deep slate text (`#18271e`) ensuring legibility in bright outdoor sunlight.
  - Micro-borders and ambient radial gradients for subtle organic depth.

---

## 📄 Complete Project Pages Catalog

### 🌾 1. Farmer Portal
- **Home Page ([`index.html`](http://localhost:3000/index.html))**: Introduction, N-P-K nutrient benefits, 4-step workflow, and login/register CTAs.
- **Farmer Registration ([`register.html`](http://localhost:3000/register.html))**: Instant 10-digit mobile number and password validation.
- **Farmer Login ([`login.html`](http://localhost:3000/login.html))**: Secure mobile session sign in.
- **Farmer Dashboard ([`dashboard.html`](http://localhost:3000/dashboard.html))**: Welcome greeting, active appointment status banner, and quick action cards.
- **Book Soil Test ([`book-appointment.html`](http://localhost:3000/book-appointment.html))**: Plot/land booking form with future date restriction and practical soil sampling guidelines.
- **My Appointments ([`appointments.html`](http://localhost:3000/appointments.html))**: Status tracking cards with filter tabs (`Pending`, `Approved`, `Rejected`, `Completed`).
- **My Reports ([`reports.html`](http://localhost:3000/reports.html))**: Verified PDF soil health reports for download with strict account privacy.

### 🛡️ 2. Admin & Coordinator Portal
- **Admin Sign In ([`admin-login.html`](http://localhost:3000/admin-login.html))**: Dedicated administrator authentication.
- **Admin Dashboard ([`admin-dashboard.html`](http://localhost:3000/admin-dashboard.html))**: Real-time KPI metric overview (Pending, Approved, Completed, Farmers) and recent requests.
- **Appointment Management ([`admin-appointments.html`](http://localhost:3000/admin-appointments.html))**: Review, approve, reject, or mark appointments completed with interactive controls.
- **Upload Reports ([`admin-reports.html`](http://localhost:3000/admin-reports.html))**: Upload lab-verified PDF reports linked to completed appointments.
- **Farmer Directory ([`admin-farmers.html`](http://localhost:3000/admin-farmers.html))**: Searchable list of registered farmers with contact links.

### 📚 3. Community Knowledge & Utility
- **Soil Health Guide ([`soil-guide.html`](http://localhost:3000/soil-guide.html))**: Visual guide on N-P-K balance, pH meter scale, and field sampling techniques.
- **404 Not Found ([`404.html`](http://localhost:3000/404.html))**: Friendly glassmorphic error page.

---

## 🏷️ Approved Appointment Statuses

Four agreed statuses with high-contrast color badges:

1. **`Pending`** (Amber / `#b45309`): Awaiting coordinator review.
2. **`Approved`** (Blue / `#0369a1`): Approved; sample collection in progress.
3. **`Rejected`** (Crimson / `#be123c`): Declined with re-booking option.
4. **`Completed`** (Green / `#15803d`): Tested and official report published.

---

## 🚀 How to Run

1. **Start Local Preview Server**:
   ```bash
   python3 -m http.server 3000
   ```
2. **Open in Browser**:
   [http://localhost:3000](http://localhost:3000)

3. **Run Automated Test Suite**:
   ```bash
   bash tests/run_all_tests.sh
   ```
