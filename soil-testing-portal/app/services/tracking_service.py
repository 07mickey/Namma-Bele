import json
from datetime import datetime, timezone
import random

STAGE_DEFINITIONS = {
    1: {"name": "APPOINTMENT_REQUESTED", "dept": "Customer Service", "desc": "Appointment request submitted by farmer or assisted operator."},
    2: {"name": "APPOINTMENT_CONFIRMED", "dept": "Operations Planning", "desc": "Appointment verified and confirmed by operations team."},
    3: {"name": "FIELD_WORKER_ASSIGNED", "dept": "Field Operations", "desc": "Designated field technician assigned for on-site sample collection."},
    4: {"name": "VISIT_SCHEDULED", "dept": "Field Operations", "desc": "Field visit scheduled for designated date and time window."},
    5: {"name": "SAMPLE_COLLECTED", "dept": "Field Operations", "desc": "Soil core sample extracted from farm plot with GPS and depth coordinates."},
    6: {"name": "SAMPLE_IN_TRANSIT", "dept": "Logistics & Transport", "desc": "Sample sealed in barcoded tamper-evident bag and dispatched to laboratory."},
    7: {"name": "SAMPLE_RECEIVED_LAB", "dept": "Laboratory Services", "desc": "Sample received, inspected, and logged into laboratory intake registry."},
    8: {"name": "LAB_ANALYSIS_IN_PROGRESS", "dept": "Laboratory Services", "desc": "Sample dried, sieved, and prepared for chemical assay analysis."},
    9: {"name": "TEST_RESULTS_RECORDED", "dept": "Laboratory Services", "desc": "Chemical assays (pH, EC, OC, N, P, K) analyzed and recorded."},
    10: {"name": "REPORT_UNDER_REVIEW", "dept": "Quality Assurance", "desc": "Test results submitted to agricultural scientist for verification and review."},
    11: {"name": "REPORT_AUTHORIZED", "dept": "Scientific Certification", "desc": "Soil health report approved, digitally signed, and published."},
    12: {"name": "PHYSICAL_REPORT_PRINTED", "dept": "Postal Logistics", "desc": "Hardcopy report printed and prepared for Speed Post consignment."},
    13: {"name": "REPORT_DELIVERED", "dept": "India Post Speed Post", "desc": "Soil health card delivered to farmer's registered delivery address."},
}


def generate_sample_code(db, appointment_id):
    """Generates a unique sample code e.g. SMP-2026-00042."""
    year = datetime.now().year
    return f"SMP-{year}-{appointment_id:05d}"


def get_or_create_soil_sample(db, appointment_id, assigned_lab_id=None):
    """
    Finds existing soil sample record or creates one linked to the appointment.
    """
    row = db.execute("SELECT * FROM soil_samples WHERE appointment_id = ?", (appointment_id,)).fetchone()
    if row:
        return row

    sample_code = generate_sample_code(db, appointment_id)
    # Pick first active lab if not specified
    if not assigned_lab_id:
        lab = db.execute("SELECT id FROM laboratories WHERE is_active = 1 ORDER BY id ASC LIMIT 1").fetchone()
        assigned_lab_id = lab["id"] if lab else None

    cursor = db.execute(
        """
        INSERT INTO soil_samples (appointment_id, sample_code, assigned_lab_id, sample_status)
        VALUES (?, ?, ?, 'Collected')
        """,
        (appointment_id, sample_code, assigned_lab_id),
    )
    db.commit()
    return db.execute("SELECT * FROM soil_samples WHERE id = ?", (cursor.lastrowid,)).fetchone()


def record_sample_event(
    db,
    sample_id,
    stage_number,
    status="COMPLETED",
    actor_user_id=None,
    actor_role="system",
    department=None,
    description=None,
    details_dict=None,
):
    """
    Appends an immutable tracking event to sample_events.
    """
    meta = STAGE_DEFINITIONS.get(stage_number, {
        "name": f"STAGE_{stage_number}",
        "dept": "Operations",
        "desc": "Event logged.",
    })
    stage_name = meta["name"]
    department = department or meta["dept"]
    description = description or meta["desc"]
    details_json = json.dumps(details_dict) if details_dict else None

    with db:
        db.execute(
            """
            INSERT INTO sample_events (
                sample_id, stage_number, stage_name, status,
                actor_user_id, actor_role, department, description, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (sample_id, stage_number, stage_name, status, actor_user_id, actor_role, department, description, details_json),
        )


def build_full_timeline(db, appointment_id):
    """
    Constructs the 13-stage timeline for a given appointment, incorporating:
    - Recorded events
    - Field visit status
    - Laboratory test status
    - Dispatch status
    """
    sample = db.execute("SELECT * FROM soil_samples WHERE appointment_id = ?", (appointment_id,)).fetchone()
    appt = db.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,)).fetchone()
    visit = db.execute("SELECT * FROM field_visits WHERE appointment_id = ?", (appointment_id,)).fetchone()
    report = db.execute("SELECT * FROM reports WHERE appointment_id = ?", (appointment_id,)).fetchone()
    dispatch = db.execute("SELECT * FROM report_dispatches WHERE appointment_id = ?", (appointment_id,)).fetchone()

    events_by_stage = {}
    if sample:
        rows = db.execute(
            """
            SELECT stage_number, stage_name, status, actor_role, department, description, details_json, created_at
            FROM sample_events
            WHERE sample_id = ?
            ORDER BY stage_number ASC, id ASC
            """,
            (sample["id"],),
        ).fetchall()
        for r in rows:
            events_by_stage[r["stage_number"]] = r

    # Determine highest completed stage
    max_completed_stage = 1
    if appt:
        max_completed_stage = 1
        if appt["status"] in ("Approved", "Completed"):
            max_completed_stage = max(max_completed_stage, 2)
    if visit:
        if visit["assigned_worker_id"]:
            max_completed_stage = max(max_completed_stage, 3)
        if visit["scheduled_date"]:
            max_completed_stage = max(max_completed_stage, 4)
        if visit["visit_status"] == "Completed":
            max_completed_stage = max(max_completed_stage, 5)
    if sample:
        if sample["sample_status"] == "In_Transit":
            max_completed_stage = max(max_completed_stage, 6)
        elif sample["sample_status"] in ("Received", "Testing"):
            max_completed_stage = max(max_completed_stage, 7)
    if sample:
        assay = db.execute("SELECT * FROM lab_test_assays WHERE sample_id = ?", (sample["id"],)).fetchone()
        if assay:
            max_completed_stage = max(max_completed_stage, 9)
            if assay["lab_status"] == "Authorized":
                max_completed_stage = max(max_completed_stage, 11)
            else:
                max_completed_stage = max(max_completed_stage, 10)
    if report:
        max_completed_stage = max(max_completed_stage, 11)
    if dispatch:
        if dispatch["dispatch_status"] == "Printed":
            max_completed_stage = max(max_completed_stage, 12)
        elif dispatch["dispatch_status"] == "Dispatched":
            max_completed_stage = max(max_completed_stage, 12)
        elif dispatch["dispatch_status"] == "Delivered":
            max_completed_stage = max(max_completed_stage, 13)

    if events_by_stage:
        recorded_max = max(events_by_stage.keys())
        max_completed_stage = max(max_completed_stage, recorded_max)

    timeline = []
    for stage_num in range(1, 14):
        meta = STAGE_DEFINITIONS[stage_num]
        event_record = events_by_stage.get(stage_num)

        if stage_num < max_completed_stage:
            stage_status = "COMPLETED"
        elif stage_num == max_completed_stage:
            stage_status = "COMPLETED" if (event_record and event_record["status"] == "COMPLETED") else "IN_PROGRESS"
        else:
            stage_status = "PENDING"

        timestamp = None
        description = meta["desc"]
        details = {}

        if event_record:
            stage_status = event_record["status"]
            timestamp = event_record["created_at"]
            description = event_record["description"]
            if event_record["details_json"]:
                try:
                    details = json.loads(event_record["details_json"])
                except Exception:
                    details = {}
        elif stage_num == 1 and appt:
            timestamp = appt["created_at"]
            stage_status = "COMPLETED"
        elif stage_num == 2 and appt and appt["status"] in ("Approved", "Completed"):
            timestamp = appt["updated_at"]
            stage_status = "COMPLETED"

        timeline.append({
            "stage_number": stage_num,
            "stage_name": meta["name"],
            "department": meta["dept"],
            "title": meta["name"].replace("_", " ").title(),
            "description": description,
            "status": stage_status,
            "timestamp": timestamp,
            "details": details,
        })

    return {
        "appointment_id": appointment_id,
        "sample_code": sample["sample_code"] if sample else f"PENDING-{appointment_id}",
        "current_stage": max_completed_stage,
        "current_stage_name": STAGE_DEFINITIONS[max_completed_stage]["name"],
        "stages": timeline,
        "visit": dict(visit) if visit else None,
        "dispatch": dict(dispatch) if dispatch else None,
    }
