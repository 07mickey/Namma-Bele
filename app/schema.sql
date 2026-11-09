-- Soil Testing Appointment & Report Access Portal
-- Database Schema for SQLite (Expanded Operational & Agricultural Architecture)

-- Enforce foreign key constraints
PRAGMA foreign_keys = ON;

-- ============================================================================
-- 1. LABORATORIES TABLE
-- Registered district and regional soil testing laboratories.
-- ============================================================================
CREATE TABLE IF NOT EXISTS laboratories (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    code          TEXT NOT NULL UNIQUE,
    district      TEXT NOT NULL,
    address       TEXT NOT NULL,
    contact_phone TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);

-- ============================================================================
-- 2. USERS TABLE
-- Stores accounts for farmers, operators, field workers, lab staff, advisors, admins.
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               TEXT NOT NULL,
    phone              TEXT NOT NULL UNIQUE,
    password_hash      TEXT NOT NULL,
    role               TEXT NOT NULL DEFAULT 'farmer' 
                       CHECK (role IN ('farmer', 'admin', 'operator', 'field_worker', 'lab_staff', 'advisor')),
    account_status     TEXT NOT NULL DEFAULT 'ACTIVE'
                       CHECK (account_status IN ('ACTIVE', 'UNCLAIMED', 'SUSPENDED')),
    created_by_user_id INTEGER,
    assigned_lab_id    INTEGER,
    preferred_language TEXT NOT NULL DEFAULT 'en',
    created_at         TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_lab_id) REFERENCES laboratories (id) ON DELETE SET NULL
);

-- ============================================================================
-- 3. FARMER DELIVERY ADDRESSES TABLE
-- Residential & postal delivery addresses separate from agricultural land coordinates.
-- ============================================================================
CREATE TABLE IF NOT EXISTS farmer_delivery_addresses (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    farmer_id          INTEGER NOT NULL,
    recipient_name     TEXT NOT NULL,
    recipient_phone    TEXT NOT NULL,
    house_details      TEXT NOT NULL,
    street_or_village  TEXT NOT NULL,
    landmark           TEXT,
    taluk              TEXT NOT NULL,
    district           TEXT NOT NULL,
    state              TEXT NOT NULL DEFAULT 'Karnataka',
    pincode            TEXT NOT NULL,
    is_default         INTEGER NOT NULL DEFAULT 0,
    created_at         TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (farmer_id) REFERENCES users (id) ON DELETE CASCADE
);

-- ============================================================================
-- 4. FARMER ACCOUNT ACTIVATIONS TABLE
-- Secure OTP / claim tokens for assisted-registration farmers claiming online access.
-- ============================================================================
CREATE TABLE IF NOT EXISTS farmer_account_activations (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    farmer_id          INTEGER NOT NULL UNIQUE,
    claim_token_hash   TEXT NOT NULL,
    otp_hash           TEXT NOT NULL,
    expires_at         TEXT NOT NULL,
    attempts_remaining INTEGER NOT NULL DEFAULT 5,
    created_at         TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (farmer_id) REFERENCES users (id) ON DELETE CASCADE
);

-- ============================================================================
-- 5. FARM PLOTS TABLE
-- Agricultural land holdings with survey numbers, acreage, soil and water details.
-- ============================================================================
CREATE TABLE IF NOT EXISTS farm_plots (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    farmer_id          INTEGER NOT NULL,
    plot_name          TEXT NOT NULL,
    survey_number      TEXT NOT NULL,
    area               REAL NOT NULL CHECK (area > 0),
    area_unit          TEXT NOT NULL DEFAULT 'Acres' CHECK (area_unit IN ('Acres', 'Guntas', 'Hectares')),
    soil_type          TEXT NOT NULL DEFAULT 'Red Sandy Loam',
    irrigation_source  TEXT NOT NULL DEFAULT 'Rainfed' CHECK (irrigation_source IN ('Rainfed', 'Borewell', 'Canal', 'Drip', 'Sprinkler', 'Well')),
    landmark           TEXT,
    taluk              TEXT,
    district           TEXT,
    created_at         TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (farmer_id) REFERENCES users (id) ON DELETE CASCADE
);

-- ============================================================================
-- 6. CROP RECORDS TABLE
-- Season-by-season crop cultivation history per plot.
-- Standardizes Paddy / Rice naming.
-- ============================================================================
CREATE TABLE IF NOT EXISTS crop_records (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    farmer_id                 INTEGER NOT NULL,
    plot_id                   INTEGER NOT NULL,
    crop_name                 TEXT NOT NULL,
    variety                   TEXT,
    year                      INTEGER NOT NULL CHECK (year >= 2000 AND year <= 2100),
    season                    TEXT NOT NULL CHECK (season IN ('Kharif', 'Rabi', 'Zaid', 'Summer', 'Perennial')),
    sowing_date               TEXT,
    harvest_date              TEXT,
    actual_harvested_quantity REAL DEFAULT 0.0 CHECK (actual_harvested_quantity >= 0),
    quantity_unit             TEXT NOT NULL DEFAULT 'Quintals' CHECK (quantity_unit IN ('Quintals', 'Kg', 'Tonnes', 'Bags')),
    notes                     TEXT,
    created_at                TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (farmer_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (plot_id) REFERENCES farm_plots (id) ON DELETE CASCADE
);

-- ============================================================================
-- 7. HARVEST RECORDS TABLE
-- Harvest yields logged per crop record.
-- ============================================================================
CREATE TABLE IF NOT EXISTS harvest_records (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    crop_record_id   INTEGER NOT NULL,
    harvest_date     TEXT NOT NULL,
    total_quantity   REAL NOT NULL CHECK (total_quantity > 0),
    quantity_unit    TEXT NOT NULL DEFAULT 'Quintals' CHECK (quantity_unit IN ('Quintals', 'Kg', 'Tonnes', 'Bags')),
    quality_grade    TEXT DEFAULT 'Grade A' CHECK (quality_grade IN ('Grade A', 'Grade B', 'Grade C', 'Standard')),
    storage_location TEXT,
    notes            TEXT,
    created_at       TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (crop_record_id) REFERENCES crop_records (id) ON DELETE CASCADE
);

-- ============================================================================
-- 8. SALES RECORDS TABLE
-- Transparent sales records: gross revenue calculated as (quantity_sold * price_per_unit).
-- Must never label gross revenue as profit.
-- ============================================================================
CREATE TABLE IF NOT EXISTS sales_records (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    crop_record_id   INTEGER NOT NULL,
    sale_date        TEXT NOT NULL,
    quantity_sold    REAL NOT NULL CHECK (quantity_sold > 0),
    price_per_unit   REAL NOT NULL CHECK (price_per_unit > 0),
    gross_revenue    REAL NOT NULL CHECK (gross_revenue >= 0),
    buyer_market     TEXT NOT NULL,
    payment_status   TEXT NOT NULL DEFAULT 'Received' CHECK (payment_status IN ('Received', 'Pending', 'Partial')),
    notes            TEXT,
    created_at       TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (crop_record_id) REFERENCES crop_records (id) ON DELETE CASCADE
);

-- ============================================================================
-- 9. APPOINTMENTS TABLE
-- Tracks soil sample collection bookings made by farmers or assisted by operators.
-- ============================================================================
CREATE TABLE IF NOT EXISTS appointments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    farmer_id           INTEGER NOT NULL,
    land_details        TEXT NOT NULL,
    address             TEXT NOT NULL,
    preferred_date      TEXT NOT NULL,
    preferred_time      TEXT NOT NULL 
                        CHECK (preferred_time IN ('09:00-12:00', '14:00-17:00')),
    notes               TEXT,
    status              TEXT NOT NULL DEFAULT 'Pending' 
                        CHECK (status IN ('Pending', 'Approved', 'Rejected', 'Completed')),
    plot_id             INTEGER,
    delivery_address_id INTEGER,
    created_at          TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    updated_at          TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (farmer_id) REFERENCES users (id) ON DELETE RESTRICT,
    FOREIGN KEY (plot_id) REFERENCES farm_plots (id) ON DELETE SET NULL,
    FOREIGN KEY (delivery_address_id) REFERENCES farmer_delivery_addresses (id) ON DELETE SET NULL
);

-- ============================================================================
-- 10. FIELD VISITS TABLE
-- Field worker assignment and sample collection visit tracking.
-- ============================================================================
CREATE TABLE IF NOT EXISTS field_visits (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id     INTEGER NOT NULL UNIQUE,
    assigned_worker_id INTEGER,
    scheduled_date     TEXT NOT NULL,
    scheduled_slot     TEXT NOT NULL CHECK (scheduled_slot IN ('09:00-12:00', '14:00-17:00')),
    visit_status       TEXT NOT NULL DEFAULT 'Scheduled' 
                       CHECK (visit_status IN ('Scheduled', 'In_Progress', 'Completed', 'Cancelled', 'Rescheduled')),
    survey_number      TEXT,
    gps_latitude       REAL,
    gps_longitude      REAL,
    worker_notes       TEXT,
    completed_at       TEXT,
    created_at         TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_worker_id) REFERENCES users (id) ON DELETE SET NULL
);

-- ============================================================================
-- 11. SOIL SAMPLES TABLE
-- Physical sample metadata tagged with unique sample code.
-- ============================================================================
CREATE TABLE IF NOT EXISTS soil_samples (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id    INTEGER NOT NULL,
    visit_id          INTEGER,
    sample_code       TEXT NOT NULL UNIQUE,
    assigned_lab_id   INTEGER,
    sampling_depth_cm REAL DEFAULT 15.0,
    soil_appearance   TEXT,
    sample_status     TEXT NOT NULL DEFAULT 'Collected' 
                      CHECK (sample_status IN ('Collected', 'In_Transit', 'Received', 'Testing', 'Completed', 'Rejected')),
    collected_at      TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    created_at        TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE CASCADE,
    FOREIGN KEY (visit_id) REFERENCES field_visits (id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_lab_id) REFERENCES laboratories (id) ON DELETE SET NULL
);

-- ============================================================================
-- 12. SAMPLE EVENTS TABLE
-- Immutable 13-stage timeline event audit trail for sample tracking.
-- Stages:
--   1: APPOINTMENT_REQUESTED
--   2: APPOINTMENT_CONFIRMED
--   3: FIELD_WORKER_ASSIGNED
--   4: VISIT_SCHEDULED
--   5: SAMPLE_COLLECTED
--   6: SAMPLE_IN_TRANSIT
--   7: SAMPLE_RECEIVED_LAB
--   8: LAB_ANALYSIS_IN_PROGRESS
--   9: TEST_RESULTS_RECORDED
--  10: REPORT_UNDER_REVIEW
--  11: REPORT_AUTHORIZED
--  12: PHYSICAL_REPORT_PRINTED
--  13: REPORT_DELIVERED
-- ============================================================================
CREATE TABLE IF NOT EXISTS sample_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id     INTEGER NOT NULL,
    stage_number  INTEGER NOT NULL CHECK (stage_number BETWEEN 1 AND 13),
    stage_name    TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'COMPLETED' CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED')),
    actor_user_id INTEGER,
    actor_role    TEXT NOT NULL,
    department    TEXT NOT NULL,
    description   TEXT NOT NULL,
    details_json  TEXT,
    created_at    TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (sample_id) REFERENCES soil_samples (id) ON DELETE CASCADE,
    FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- ============================================================================
-- 13. LAB TEST ASSAYS TABLE
-- Chemical test measurements (pH, EC, OC, N, P, K) with scientific ratings.
-- ============================================================================
CREATE TABLE IF NOT EXISTS lab_test_assays (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id            INTEGER NOT NULL UNIQUE,
    lab_id               INTEGER NOT NULL,
    tested_by_user_id    INTEGER NOT NULL,
    ph_value             REAL NOT NULL CHECK (ph_value >= 0.0 AND ph_value <= 14.0),
    ec_ds_m              REAL NOT NULL CHECK (ec_ds_m >= 0.0),
    organic_carbon_pct   REAL NOT NULL CHECK (organic_carbon_pct >= 0.0 AND organic_carbon_pct <= 100.0),
    nitrogen_kg_ha       REAL NOT NULL CHECK (nitrogen_kg_ha >= 0.0),
    phosphorus_kg_ha     REAL NOT NULL CHECK (phosphorus_kg_ha >= 0.0),
    potassium_kg_ha      REAL NOT NULL CHECK (potassium_kg_ha >= 0.0),
    ph_rating            TEXT NOT NULL,
    ec_rating            TEXT NOT NULL,
    oc_rating            TEXT NOT NULL,
    n_rating             TEXT NOT NULL,
    p_rating             TEXT NOT NULL,
    k_rating             TEXT NOT NULL,
    lab_status           TEXT NOT NULL DEFAULT 'Submitted' 
                         CHECK (lab_status IN ('Draft', 'Submitted', 'Authorized', 'Rejected')),
    authorized_by_user_id INTEGER,
    authorized_at        TEXT,
    remarks              TEXT,
    completed_at         TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    created_at           TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (sample_id) REFERENCES soil_samples (id) ON DELETE CASCADE,
    FOREIGN KEY (lab_id) REFERENCES laboratories (id) ON DELETE RESTRICT,
    FOREIGN KEY (tested_by_user_id) REFERENCES users (id) ON DELETE RESTRICT,
    FOREIGN KEY (authorized_by_user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- ============================================================================
-- 14. REPORTS TABLE
-- Secure PDF reports and digital test report references.
-- Preserves existing columns and referential constraints.
-- ============================================================================
CREATE TABLE IF NOT EXISTS reports (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id    INTEGER NOT NULL UNIQUE,
    file_path         TEXT NOT NULL UNIQUE,
    original_filename TEXT NOT NULL,
    file_size_bytes   INTEGER NOT NULL CHECK (file_size_bytes > 0),
    checksum_sha256   TEXT NOT NULL,
    uploaded_by       INTEGER NOT NULL,
    uploaded_at       TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    assay_id          INTEGER,
    authorized_by     INTEGER,
    authorized_at     TEXT,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE RESTRICT,
    FOREIGN KEY (uploaded_by) REFERENCES users (id) ON DELETE RESTRICT,
    FOREIGN KEY (assay_id) REFERENCES lab_test_assays (id) ON DELETE SET NULL,
    FOREIGN KEY (authorized_by) REFERENCES users (id) ON DELETE SET NULL
);

-- ============================================================================
-- 15. REPORT DISPATCHES TABLE
-- Physical print queue and Speed Post tracking with immutable address snapshots.
-- ============================================================================
CREATE TABLE IF NOT EXISTS report_dispatches (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id                  INTEGER,
    appointment_id             INTEGER NOT NULL,
    recipient_name             TEXT NOT NULL,
    recipient_phone            TEXT NOT NULL,
    delivery_address_snapshot  TEXT NOT NULL,
    courier_service            TEXT NOT NULL DEFAULT 'India Post Speed Post',
    tracking_number            TEXT,
    dispatch_status            TEXT NOT NULL DEFAULT 'Queued' 
                               CHECK (dispatch_status IN ('Queued', 'Printed', 'Dispatched', 'Delivered', 'Returned')),
    dispatched_at              TEXT,
    delivered_at               TEXT,
    created_at                 TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE CASCADE
);

-- ============================================================================
-- 16. EXPERT CONSULTATIONS TABLE
-- Advisory requests from farmers to qualified agricultural scientists/officers.
-- ============================================================================
CREATE TABLE IF NOT EXISTS expert_consultations (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    farmer_id            INTEGER NOT NULL,
    plot_id              INTEGER,
    report_id            INTEGER,
    category             TEXT NOT NULL 
                         CHECK (category IN ('Crop Recommendation', 'Soil Health', 'Pest Control', 'Fertilizer Application', 'Irrigation', 'General Advice')),
    subject              TEXT NOT NULL,
    question_text        TEXT NOT NULL,
    status               TEXT NOT NULL DEFAULT 'OPEN' 
                         CHECK (status IN ('OPEN', 'IN_REVIEW', 'ANSWERED', 'CLOSED')),
    assigned_advisor_id  INTEGER,
    created_at           TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    updated_at           TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (farmer_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (plot_id) REFERENCES farm_plots (id) ON DELETE SET NULL,
    FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_advisor_id) REFERENCES users (id) ON DELETE SET NULL
);

-- ============================================================================
-- 17. CONSULTATION MESSAGES TABLE
-- Conversation thread between farmer and agricultural expert.
-- ============================================================================
CREATE TABLE IF NOT EXISTS consultation_messages (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    consultation_id     INTEGER NOT NULL,
    sender_user_id      INTEGER NOT NULL,
    sender_role         TEXT NOT NULL,
    message_text        TEXT NOT NULL,
    attachment_filename TEXT,
    created_at          TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (consultation_id) REFERENCES expert_consultations (id) ON DELETE CASCADE,
    FOREIGN KEY (sender_user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- ============================================================================
-- 18. OPERATOR AUDIT LOGS TABLE
-- Audit log of operator actions (assisted registrations, bookings, lookup).
-- ============================================================================
CREATE TABLE IF NOT EXISTS operator_audit_logs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_user_id      INTEGER NOT NULL,
    actor_role         TEXT NOT NULL,
    action             TEXT NOT NULL,
    target_entity_type TEXT NOT NULL,
    target_entity_id   INTEGER,
    details_json       TEXT,
    ip_address         TEXT,
    created_at         TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_appointments_farmer_id ON appointments (farmer_id);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments (status);
CREATE INDEX IF NOT EXISTS idx_field_visits_worker ON field_visits (assigned_worker_id);
CREATE INDEX IF NOT EXISTS idx_field_visits_status ON field_visits (visit_status);
CREATE INDEX IF NOT EXISTS idx_soil_samples_appt ON soil_samples (appointment_id);
CREATE INDEX IF NOT EXISTS idx_soil_samples_code ON soil_samples (sample_code);
CREATE INDEX IF NOT EXISTS idx_sample_events_sample ON sample_events (sample_id);
CREATE INDEX IF NOT EXISTS idx_farm_plots_farmer ON farm_plots (farmer_id);
CREATE INDEX IF NOT EXISTS idx_crop_records_farmer ON crop_records (farmer_id);
CREATE INDEX IF NOT EXISTS idx_harvest_records_crop ON harvest_records (crop_record_id);
CREATE INDEX IF NOT EXISTS idx_sales_records_crop ON sales_records (crop_record_id);
CREATE INDEX IF NOT EXISTS idx_consultations_farmer ON expert_consultations (farmer_id);
CREATE INDEX IF NOT EXISTS idx_consultations_status ON expert_consultations (status);
CREATE INDEX IF NOT EXISTS idx_dispatch_status ON report_dispatches (dispatch_status);
