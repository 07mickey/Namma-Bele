# Admin UI Demonstration Guide

**Purpose:** Walk through the current frontend prototype for the admin side of the Soil Testing Appointment & Report Access Portal. All interactions are client‑side only and use demo data; no real persistence occurs.

## Prerequisites
- Open the project folder `frontend/` in a web browser (serve via a simple static server or open files directly). No backend is required.
- Ensure the browser allows loading local files (or use `python -m http.server`).

## Demonstration Sequence
1. **Open Admin Login**
   - Navigate to `frontend/admin_login.html`.
   - You will see email and password fields, a show/hide eye icon, and a **Login** button.
   - **Current limitation:** Clicking **Login** always shows an error message *“Login service not available – backend integration pending.”* No token is created.

2. **Navigate to Dashboard** (simulate successful login)
   - Manually open `frontend/admin_dashboard.html` (since real login is not implemented).
   - The sidebar highlights **Dashboard**.
   - Statistic cards display demo numbers (all `0`).
   - Recent appointments table shows demo rows populated by `admin_dashboard.js`.
   - **What works:** Layout, responsive design, navigation links.
   - **What is missing:** Real stats fetched from the backend.

3. **Farmer Management**
   - Click **Farmers** in the sidebar (or open `frontend/farmer_management.html`).
   - A table of demo farmers appears.
   - Use the **Search** box to filter by name or email – the table updates instantly.
   - Click **View** on any row to open a modal showing farmer details.
   - **Limitation:** Data is static demo data; any edit or delete actions are not implemented.

4. **Appointment Management**
   - Click **Appointments** in the sidebar (or open `frontend/appointment_management.html`).
   - The table shows demo appointments with statuses **Pending**, **Approved**, **Rejected**, **Completed**.
   - Use the **Search** box or the **Status** dropdown to filter.
   - **Actions:**
     - **View** – opens a modal with appointment details.
     - **Approve** / **Reject** – visible only for **Pending** rows. Clicking asks for confirmation; on confirm the status changes locally (demo only).
     - **Mark Completed** – visible only for **Approved** rows; works similarly.
   - **Note:** All status changes are temporary and disappear on page reload.

5. **Report Management**
   - Click **Reports** in the sidebar (or open `frontend/report_management.html`).
   - **Upload Form**:
     - Select a farmer, then an appointment (filtered by farmer).
     - Choose a **PDF** file (must be ≤ 5 MB). The form validates MIME type, size, and emptiness; errors are shown inline.
     - Click **Upload** – after a short simulated delay a new row appears in the report table (demo entry). The table shows Report ID, Farmer, Appointment ID, file name, upload date.
   - **Report Table**:
     - Search by Report ID or farmer name.
     - **View** – opens a modal with report details (safe DOM construction).
     - **Download** – creates a temporary Blob URL and triggers a download of the selected PDF (client‑side only).
     - **Replace** – prompts for a new PDF, validates it, and updates the demo entry.
   - **Limitation:** Files are never sent to a server; all operations exist only in memory for the current session.

6. **Show Documentation**
   - Open the testing and security documentation files located in `documentation/testing/`:
     - `testing_report.md` – summary of Phase 7 integration tests.
     - `security_review_report.md` – Phase 8 security findings and fixes.
   - Explain that these documents record what has been verified on the frontend and what still requires backend implementation.

## Closing Remarks
- Emphasise that **all interactions are temporary**; reloading any admin page clears the demo data.
- Mention that the next steps are to connect the UI to the Flask backend (login, data endpoints, file storage) and to replace all demo logic with real API calls.
- The demonstration should take roughly **5‑7 minutes**.

---
*Prepared by Person 3 – Admin Module, Testing & Security.*
