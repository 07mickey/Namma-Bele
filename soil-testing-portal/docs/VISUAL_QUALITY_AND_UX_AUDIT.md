# Visual Quality & User Experience Audit Report

**Project:** Soil Testing & Farmer Agricultural Service Platform  
**Workspace:** `/Users/manojv/Community Project/soil-testing-portal/`  
**Date:** November 4, 2026  
**Baseline Test Status:** 183 / 183 passed (100%)  
**Audit Purpose:** Comprehensive inspection of the public website, farmer portal, and staff operations dashboards prior to visual refinement.

---

## 1. Executive Summary

The Soil Testing Portal is functionally mature with end-to-end backend integrations across farmer booking, 13-stage sample tracking, ICAR laboratory assays, postal dispatch, and expert agronomic consultations. 

However, visual quality varies across the interface due to progressive feature additions. The public landing page benefits from M2's editorial visual design, but internal portals (Farmer, Operator, Field Worker, Laboratory, Advisor, Administrator) exhibit design debt: inconsistent typography, mismatched color tokens, variable card elevations, unstandardized buttons, unrefined table density, and fragmented mobile responsive behaviors.

This audit catalogues every visual, typographic, structural, and accessibility issue to guide the visual refinement plan.

---

## 2. Global Design System & Component Audit

### A. Color Palette Inconsistencies
- **Token Fragmentation:** `:root` in `style.css` contains overlapping color variables:
  - `--primary: #2e7d32` vs `--color-primary-green: #1e7e48`.
  - `--color-forest-green: #1b3820` vs `--primary-dark: #1b3820`.
  - `--color-bg-light` vs `--surface-bg` vs `--slate-100`.
  - `--color-border` vs `--slate-200` vs `--color-green-border`.
- **Inline Hardcoding:** Multiple templates (`farmer_farm_records.html`, `contact.html`, `advisor_dashboard.html`, `admin_dispatch.html`) bypass CSS tokens and hardcode inline colors (`#1976d2`, `#2e7d32`, `#dcfce7`, `#15803d`).
- **Excessive Gradients:** Several dashboard banners use heavy gradients that create visual noise and reduce text contrast.

### B. Typographic Hierarchy
- **Header Scale Inconsistency:** Hero titles range from `1.6rem` to `2.5rem` with inconsistent font weights (`700`, `800`, `850`).
- **Font Stacks:** Base font declarations mix system-ui and -apple-system inconsistently.
- **Micro-Copy & Badges:** Badges use varying font sizes (`0.75rem` to `0.88rem`), uppercase/lowercase styles, and padding.
- **Reading Comfort:** Some dense informational tables lack vertical breathing room, and form labels lack uniform hierarchy.

### C. Spacing & Card Overuse
- **Floating Card Fatigue:** Screens like `farmer.html` stack 6 separate floating card containers consecutively (Hero card, Navigation ribbon, Stats grid, Active status card, Action cards grid, Multi-step booking card, Appointments list card).
- **Vertical Rhythm:** Margins between sections fluctuate between `1rem`, `1.5rem`, `2rem`, `2.5rem`, and `4.5rem`.
- **Form Density:** Form rows lack consistent gutters (`gap: 1rem` vs `gap: 1.5rem`).

### D. Component Inconsistencies
- **Buttons:**
  - Inconsistent shapes: pill-shaped `.btn-pill-arrow` vs rounded `.btn` (`border-radius: 4px`) vs `.btn-sm` (`border-radius: 6px`).
  - Varying hover states and shadow intensities.
  - Inaccessible focus states on interactive buttons.
- **Form Controls:**
  - `.form-control` heights and border colors vary depending on template.
  - Radio cards in booking wizards lack crisp keyboard focus indicators.
- **Tables:**
  - Table headers use inconsistent background colors across portals (`#f8faf9`, transparent, `#f1f5f9`).
  - Cell padding ranges from `0.5rem` to `1.25rem`.
  - Long strings (land details, postal addresses) cause uneven row heights without clean truncation or tooltips.

---

## 3. Application Area Audits

### 3.1 Public Website

| Page | File | Identified Visual & UX Issues |
| :--- | :--- | :--- |
| **Landing Page** | `index.html` | - Hero title and sprout visual require balanced vertical alignment on laptop screens.<br>- Bento grid text cards and visual cards need harmonious internal padding.<br>- FAQ accordion toggle icon needs smooth rotation and zero layout shift.<br>- Footer requires clean semantic structure matching M2's calm agricultural tones. |
| **Soil Testing Guide** | `soil_guide.html` | - 3D Three.js canvas container is visually disconnected from the rest of the page.<br>- N-P-K nutrient cards have inconsistent badge placement.<br>- WebGL fallback card needs cleaner typography and better diagrammatic styling. |
| **Contact Page** | `contact.html` | - Helpline and district lab cards use mismatched top border accent colors (`#1e7e48`, `#81c784`, `#e65100`).<br>- Inline styles dominate layout structure.<br>- FAQ items duplicate layout patterns from `index.html` with different styling. |
| **Login / Register / Claim** | `login.html`<br>`register.html`<br>`claim.html` | - Dual-tab login (Farmer vs Staff) needs refined active tab indicator and smoother transitions.<br>- Account claim stepper has abrupt visibility changes without smooth fade/slide.<br>- Form inputs lack unified green focus rings. |

---

### 3.2 Farmer Portal

| View | File | Identified Visual & UX Issues |
| :--- | :--- | :--- |
| **Farmer Dashboard** | `farmer.html` | - Overcrowded top navigation ribbon wraps clumsily on tablets and mobile.<br>- Active appointment status card needs clear human-readable lifecycle text (e.g. *"Your sample has reached the laboratory"*).<br>- Booking wizard stepper lines and step circles need responsive scaling down to 360px.<br>- Time-slot radio cards need clear selected visual cues. |
| **Live Sample Tracking** | `farmer_tracking.html` | - 13-stage timeline vertical line has misaligned marker nodes on mobile viewports.<br>- Completed vs Current vs Pending steps need distinct, high-contrast markers.<br>- Search box and quick-switch buttons wrap awkwardly on mobile. |
| **Farm Plots** | `farmer_plots.html` | - Plot cards in grid have varying heights depending on notes length.<br>- Add-plot form fields lack responsive 2-column to 1-column collapse. |
| **Crop History** | `farmer_crop_history.html` | - Historical crop rotation table lacks horizontal scroll indicators on small screens.<br>- Seasonal badges (Kharif, Rabi, Summer) need unified semantic styling. |
| **Harvest & Sales** | `farmer_farm_records.html` | - KPI metrics grid displays 5 cards that crowd on medium viewports.<br>- Sales transaction modal lacks clean tabular summary. |
| **Postal Addresses** | `farmer_addresses.html` | - Saved address cards have inconsistent action button alignment.<br>- PIN code input lacks input-mask guidance. |
| **Expert Consultations** | `farmer_expert.html` | - Two-column master-detail layout collapses abruptly on tablet viewports.<br>- Question thread chat bubbles lack clear speaker differentiation. |

---

### 3.3 Staff Portals (Operator, Field Worker, Laboratory, Advisor, Admin)

| Portal | File | Operational Priority | Identified Visual & UX Issues |
| :--- | :--- | :--- | :--- |
| **Operator Desk** | `operator.html` | Search, Assisted Registration | - Search input and button wrap onto multiple lines.<br>- Assisted registration form is cramped in a 2-column layout on standard screens.<br>- Unclaimed account status lacks distinct visual indicator. |
| **Field Worker** | `field_worker.html` | Mobile Visit Execution, Sample Collection | - Table-based layout is ill-suited for on-field mobile phones.<br>- Action buttons (`Collect Sample`) need large touch targets (minimum 48px height).<br>- Root depth and core count inputs in collection modal need streamlined touch controls. |
| **Laboratory** | `lab_dashboard.html` | Sample Queue, Assay Entry | - Status dropdown and table controls lack vertical alignment.<br>- Assay input modal lacks unit indicators (`kg/ha`, `dS/m`, `pH units`) next to input fields.<br>- Dual-signoff warning needs clear, non-intrusive presentation. |
| **Advisor Desk** | `advisor_dashboard.html` | Consultation Queue, Response Composer | - Query queue items lack visual indicators for priority/age.<br>- Expert composer textarea lacks clean formatting tools and soil report reference pill. |
| **Admin Console** | `admin.html`<br>`admin_tracking.html`<br>`admin_dispatch.html` | Oversight, Queue Management, Dispatch | - Search bar, role filter, and status filter lack cohesive toolbar styling.<br>- Dispatch queue table has wide cells that force awkward scrolling.<br>- Consignment tracking input modal needs clear UPU S10 format guide. |

---

## 4. Responsive Design & Viewport Matrix

| Viewport Width | Device Target | Current Breakpoint Issues |
| :--- | :--- | :--- |
| **360px** | Small Android (Galaxy, Redmi) | Horizontal scrolling on tables; booking stepper circles overlap text labels; navigation bar overflows; hero buttons wrap awkwardly. |
| **390px** | Standard iPhone (12/13/14/15) | Form row gaps cause uneven padding; stats cards stack in uneven grids; action cards text is compressed. |
| **768px** | iPad Portrait / Small Tablet | 2-column master-detail layouts (Advisor, Expert, Operator) become uncomfortably narrow; navigation links crowd the header. |
| **1024px** | iPad Landscape / Small Laptop | Bento grid and spotlight showcase need optimal line length and margin containment. |
| **1366px & 1440px** | Desktop / Workstations | Max-width constraints vary between `1000px`, `1050px`, `1100px`, `1200px`, and full width, creating inconsistent page edges during navigation. |

---

## 5. Accessibility Audit (WCAG 2.1 AA)

1. **Color Contrast:**
   - M2's light green badges (`rgba(22, 163, 74, 0.14)` with `#15803d`) pass AA for large text, but smaller text in muted slate (`#64748b` on `#f4f7f4`) occasionally dips below 4.5:1.
2. **Keyboard Navigation & Focus:**
   - Default browser focus rings are suppressed in some components without replacement `:focus-visible` styles.
   - Accordion FAQ and booking stepper need explicit `aria-expanded` and `aria-current` states.
3. **Touch Targets:**
   - Table action buttons (`btn-sm`) currently measure ~32px in height, below the recommended 44px–48px touch target for mobile agricultural field workers.
4. **Status Indication:**
   - Some tables rely solely on badge background colors without icons or unambiguous textual labels.

---

## 6. Implementation Action Plan

1. **Group 1: Design System & Shared Navigation (`style.css`, `base.html`):**
   - Unify CSS variables under clean semantic groups (`--color-primary`, `--color-forest`, `--color-earth`, `--color-surface`, `--color-border`).
   - Standardize typography scale, font-family, and heading weights.
   - Standardize buttons (`.btn`, `.btn-primary`, `.btn-secondary`, `.btn-outline`, `.btn-pill-arrow`).
   - Create consistent input, select, textarea, and table components.
   - Unify header navigation with responsive mobile menu/scroll and standardized role badge.
   - Align content widths to a consistent `1140px` container.

2. **Group 2: Public Website Refinement:**
   - Refine `index.html` (hero triad proportions, sprout alignment, bento grid rhythm, spotlight card, FAQ accordion).
   - Refine `soil_guide.html`, `contact.html`, `login.html`, `register.html`, `claim.html`.

3. **Group 3: Farmer Portal Refinement:**
   - Streamline `farmer.html` (calm welcome header, human-readable status banner, clean service ribbon, refined booking wizard).
   - Polish `farmer_tracking.html` (high-contrast 13-stage timeline).
   - Standardize `farmer_plots.html`, `farmer_crop_history.html`, `farmer_farm_records.html`, `farmer_addresses.html`, `farmer_expert.html`.

4. **Group 4: Staff Portals Refinement:**
   - Refine Operator Desk (`operator.html`).
   - Refine Field Worker Portal (`field_worker.html` with mobile-first card list and 48px touch targets).
   - Refine Laboratory Workspace (`lab_dashboard.html` with unit tags and clear assay inputs).
   - Refine Advisor Console (`advisor_dashboard.html` with clean query queue and composer).
   - Refine Admin Console (`admin.html`, `admin_tracking.html`, `admin_dispatch.html`).

5. **Group 5: Responsive & Accessibility Polish:**
   - Audit across 360px, 390px, 768px, 1024px, 1366px, 1440px.
   - Add visible `:focus-visible` rings and `prefers-reduced-motion` compliance.

6. **Group 6: Visual Verification & Test Run:**
   - Capture AFTER screenshots for direct comparison against BEFORE screenshots.
   - Run full 183-test pytest suite.

