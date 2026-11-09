# Person 3 (M3) Contribution Archive

This directory contains the documentation, gap analysis, and integration reconciliation for the **Person 3 (M3)** contribution to the **Soil Testing Appointment & Report Access Portal**.

---

## Directory Contents

1. **[`M3_CONTRIBUTION_SUMMARY.md`](M3_CONTRIBUTION_SUMMARY.md):**
   - High-level overview of Person 3's assigned responsibilities.
   - Comprehensive inventory of the files submitted by Person 3 in `sidhan/Soil-Testing-Portal/`.
   - Identification of visual, UX, and testing concepts accepted into the main project.
2. **[`M3_RECONCILIATION_NOTES.md`](M3_RECONCILIATION_NOTES.md):**
   - Technical and architectural reconciliation between M3's prototype and the authoritative Flask codebase.
   - Detailed rationale for why proposed JWT authentication, email credentials, farmer/appointment deletions, and report replacements were rejected.
   - Image provenance audit documenting why unverified, low-resolution thumbnail assets were not integrated.

---

## Authority & Non-Regression Notice

> [!IMPORTANT]
> The authoritative implementation of the Soil Testing Portal is contained strictly within `soil-testing-portal/`. The standalone HTML and JavaScript files in `sidhan/Soil-Testing-Portal/` served as conceptual prototypes. Any historical proposals from M3 advocating JWTs, CORS for separated origins, or database schema modifications are non-authoritative and superseded by the approved project specifications in `docs/`.

