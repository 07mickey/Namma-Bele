import os
import sys
import sqlite3
import tempfile
import pytest

# Ensure the soil-testing-portal directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.db import get_db, init_db, close_db
from werkzeug.security import check_password_hash


@pytest.fixture
def app_and_db():
    """
    Creates and configures an isolated Flask test application
    with a fresh, dedicated temporary database file.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_soil_testing.db")
        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
        })

        with app.app_context():
            init_db()

        yield app, db_path


@pytest.fixture
def app(app_and_db):
    app, _ = app_and_db
    return app


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


def insert_user(db, name="Test Farmer", phone="+919876543210", role="farmer"):
    """Helper to insert a user record for testing."""
    cursor = db.execute(
        "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, ?)",
        (name, phone, "pbkdf2:sha256:dummy_test_hash", role),
    )
    db.commit()
    return cursor.lastrowid


def insert_appointment(
    db,
    farmer_id,
    land_details="10 acres wheat field",
    address="Village Green, Field 4",
    preferred_date="2026-11-15",
    preferred_time="09:00-12:00",
    status="Pending",
):
    """Helper to insert an appointment record for testing."""
    cursor = db.execute(
        """
        INSERT INTO appointments (
            farmer_id, land_details, address, preferred_date, preferred_time, status
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (farmer_id, land_details, address, preferred_date, preferred_time, status),
    )
    db.commit()
    return cursor.lastrowid


# ============================================================================
# 1. DATABASE INITIALIZATION & REPEATABILITY TESTS
# ============================================================================

def test_init_db_creates_tables_and_indexes(app):
    """Test that init_db creates all required tables and indexes."""
    with app.app_context():
        db = get_db()
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [row["name"] for row in tables]

        assert "users" in table_names
        assert "appointments" in table_names
        assert "reports" in table_names

        indexes = db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
        ).fetchall()
        index_names = [row["name"] for row in indexes]

        assert "idx_appointments_farmer_id" in index_names
        assert "idx_appointments_status" in index_names


def test_init_db_repeated_execution_is_safe(app):
    """Test that calling init_db repeatedly is idempotent and preserves existing data."""
    with app.app_context():
        # Insert a record into the initialized database
        insert_user(get_db(), name="Persistent Farmer", phone="+919876543201")

        # Run initialization again to verify safe repeatability and data preservation
        init_db()

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE phone = ?", ("+919876543201",)).fetchone()
        assert user is not None
        assert user["name"] == "Persistent Farmer"


def test_init_db_cli_command(runner):
    """Test the 'flask init-db' CLI command output."""
    result = runner.invoke(args=["init-db"])
    assert result.exit_code == 0
    assert "Initialized the database." in result.output


# ============================================================================
# 2. CONSTRAINTS TESTS: USERS TABLE
# ============================================================================

def test_unique_phone_constraint(app):
    """Test that duplicate phone numbers are rejected by UNIQUE constraint."""
    with app.app_context():
        db = get_db()
        insert_user(db, name="Farmer One", phone="+919876543210")

        with pytest.raises(sqlite3.IntegrityError):
            insert_user(db, name="Farmer Two", phone="+919876543210")


def test_valid_and_invalid_user_roles(app):
    """Test that only 'farmer' and 'admin' roles are accepted."""
    with app.app_context():
        db = get_db()
        # Valid roles
        farmer_id = insert_user(db, name="Farmer A", phone="+919876543211", role="farmer")
        admin_id = insert_user(db, name="Admin A", phone="+919876543212", role="admin")
        assert farmer_id is not None
        assert admin_id is not None

        # Invalid role should fail CHECK constraint
        with pytest.raises(sqlite3.IntegrityError):
            insert_user(db, name="Hacker", phone="+919876543213", role="superadmin")

        with pytest.raises(sqlite3.IntegrityError):
            insert_user(db, name="Guest", phone="+919876543214", role="guest")


# ============================================================================
# 3. CONSTRAINTS TESTS: APPOINTMENTS TABLE
# ============================================================================

def test_valid_and_invalid_appointment_statuses(app):
    """Test that allowed statuses ('Pending', 'Approved', 'Rejected', 'Completed') pass and others fail."""
    with app.app_context():
        db = get_db()
        farmer_id = insert_user(db, name="Farmer Bob", phone="+919876543220")

        # Valid statuses
        for valid_status in ["Pending", "Approved", "Rejected", "Completed"]:
            appt_id = insert_appointment(db, farmer_id=farmer_id, status=valid_status)
            assert appt_id is not None

        # Invalid statuses should fail CHECK constraint
        with pytest.raises(sqlite3.IntegrityError):
            insert_appointment(db, farmer_id=farmer_id, status="Cancelled")

        with pytest.raises(sqlite3.IntegrityError):
            insert_appointment(db, farmer_id=farmer_id, status="In_Progress")


def test_valid_and_invalid_time_slots(app):
    """Test that only '09:00-12:00' and '14:00-17:00' time slots are permitted."""
    with app.app_context():
        db = get_db()
        farmer_id = insert_user(db, name="Farmer Tim", phone="+919876543230")

        # Valid time slots
        appt1 = insert_appointment(db, farmer_id=farmer_id, preferred_time="09:00-12:00")
        appt2 = insert_appointment(db, farmer_id=farmer_id, preferred_time="14:00-17:00")
        assert appt1 is not None
        assert appt2 is not None

        # Invalid time slots should fail CHECK constraint
        with pytest.raises(sqlite3.IntegrityError):
            insert_appointment(db, farmer_id=farmer_id, preferred_time="10:00-11:00")

        with pytest.raises(sqlite3.IntegrityError):
            insert_appointment(db, farmer_id=farmer_id, preferred_time="Evening")


# ============================================================================
# 4. FOREIGN KEY & REFERENTIAL INTEGRITY TESTS
# ============================================================================

def test_foreign_key_enforcement_on_insert(app):
    """Test that inserting records with non-existent foreign keys fails."""
    with app.app_context():
        db = get_db()

        # Non-existent farmer_id
        with pytest.raises(sqlite3.IntegrityError):
            insert_appointment(db, farmer_id=99999)

        # Create valid farmer and appointment, and valid admin
        farmer_id = insert_user(db, name="Farmer Real", phone="+919876543240")
        appt_id = insert_appointment(db, farmer_id=farmer_id, status="Completed")
        admin_id = insert_user(db, name="Admin Real", phone="+919876543241", role="admin")

        # Non-existent appointment_id on report
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """
                INSERT INTO reports (
                    appointment_id, file_path, original_filename, file_size_bytes, checksum_sha256, uploaded_by
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (88888, "instance/reports/test.pdf", "report.pdf", 1024, "dummy_hash", admin_id),
            )
            db.commit()

        # Non-existent uploaded_by (admin) on report
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """
                INSERT INTO reports (
                    appointment_id, file_path, original_filename, file_size_bytes, checksum_sha256, uploaded_by
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (appt_id, "instance/reports/test2.pdf", "report.pdf", 1024, "dummy_hash", 77777),
            )
            db.commit()


def test_foreign_key_on_delete_restrict(app):
    """Test that ON DELETE RESTRICT prevents deleting referenced records."""
    with app.app_context():
        db = get_db()
        farmer_id = insert_user(db, name="Farmer Parent", phone="+919876543250")
        appt_id = insert_appointment(db, farmer_id=farmer_id, status="Completed")
        admin_id = insert_user(db, name="Admin Parent", phone="+919876543251", role="admin")

        # Attempting to delete farmer while appointment exists must fail
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM users WHERE id = ?", (farmer_id,))
            db.commit()

        # Add report
        db.execute(
            """
            INSERT INTO reports (
                appointment_id, file_path, original_filename, file_size_bytes, checksum_sha256, uploaded_by
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (appt_id, "instance/reports/sample.pdf", "sample.pdf", 2048, "dummy_sha256", admin_id),
        )
        db.commit()

        # Attempting to delete appointment while report exists must fail
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM appointments WHERE id = ?", (appt_id,))
            db.commit()


def test_admin_deletion_restricted_when_reports_exist(app):
    """Test that ON DELETE RESTRICT prevents deleting an admin who uploaded a report."""
    with app.app_context():
        db = get_db()
        farmer_id = insert_user(db, name="Farmer Owner", phone="+919876543255")
        admin_id = insert_user(db, name="Admin Staff", phone="+919876543256", role="admin")
        appt_id = insert_appointment(db, farmer_id=farmer_id, status="Completed")

        # Admin uploads report
        db.execute(
            """
            INSERT INTO reports (
                appointment_id, file_path, original_filename, file_size_bytes, checksum_sha256, uploaded_by
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (appt_id, "instance/reports/admin_del.pdf", "report.pdf", 1024, "dummy_hash", admin_id),
        )
        db.commit()

        # Attempting to delete the admin user who uploaded the report must fail
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM users WHERE id = ?", (admin_id,))
            db.commit()


# ============================================================================
# 5. CONSTRAINTS TESTS: REPORTS TABLE
# ============================================================================

def test_unique_report_per_appointment(app):
    """Test that one appointment can produce at most one report."""
    with app.app_context():
        db = get_db()
        farmer_id = insert_user(db, name="Farmer Rep", phone="+919876543260")
        appt_id = insert_appointment(db, farmer_id=farmer_id, status="Completed")
        admin_id = insert_user(db, name="Admin Rep", phone="+919876543261", role="admin")

        # First report succeeds
        db.execute(
            """
            INSERT INTO reports (
                appointment_id, file_path, original_filename, file_size_bytes, checksum_sha256, uploaded_by
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (appt_id, "instance/reports/first.pdf", "first.pdf", 1024, "hash1", admin_id),
        )
        db.commit()

        # Second report for the same appointment must fail due to UNIQUE(appointment_id)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """
                INSERT INTO reports (
                    appointment_id, file_path, original_filename, file_size_bytes, checksum_sha256, uploaded_by
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (appt_id, "instance/reports/second.pdf", "second.pdf", 2048, "hash2", admin_id),
            )
            db.commit()


def test_unique_report_file_path(app):
    """Test that duplicate report file_path values are rejected by UNIQUE constraint."""
    with app.app_context():
        db = get_db()
        farmer_id = insert_user(db, name="Farmer Path", phone="+919876543265")
        admin_id = insert_user(db, name="Admin Path", phone="+919876543266", role="admin")
        appt1 = insert_appointment(db, farmer_id=farmer_id, status="Completed")
        appt2 = insert_appointment(db, farmer_id=farmer_id, status="Completed")

        # First report
        db.execute(
            """
            INSERT INTO reports (
                appointment_id, file_path, original_filename, file_size_bytes, checksum_sha256, uploaded_by
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (appt1, "instance/reports/same_path.pdf", "report1.pdf", 1024, "hash1", admin_id),
        )
        db.commit()

        # Second report with identical file_path must fail UNIQUE(file_path)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """
                INSERT INTO reports (
                    appointment_id, file_path, original_filename, file_size_bytes, checksum_sha256, uploaded_by
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (appt2, "instance/reports/same_path.pdf", "report2.pdf", 2048, "hash2", admin_id),
            )
            db.commit()


def test_positive_file_size_constraint(app):
    """Test that file_size_bytes must be strictly positive (> 0)."""
    with app.app_context():
        db = get_db()
        farmer_id = insert_user(db, name="Farmer Size", phone="+919876543270")
        admin_id = insert_user(db, name="Admin Size", phone="+919876543271", role="admin")
        appt1 = insert_appointment(db, farmer_id=farmer_id, status="Completed")
        appt2 = insert_appointment(db, farmer_id=farmer_id, status="Completed")

        # Zero bytes must fail CHECK (file_size_bytes > 0)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """
                INSERT INTO reports (
                    appointment_id, file_path, original_filename, file_size_bytes, checksum_sha256, uploaded_by
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (appt1, "instance/reports/zero.pdf", "zero.pdf", 0, "hash_zero", admin_id),
            )
            db.commit()

        # Negative bytes must fail CHECK (file_size_bytes > 0)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """
                INSERT INTO reports (
                    appointment_id, file_path, original_filename, file_size_bytes, checksum_sha256, uploaded_by
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (appt2, "instance/reports/neg.pdf", "neg.pdf", -500, "hash_neg", admin_id),
            )
            db.commit()


# ============================================================================
# 6. TRANSACTION ROLLBACK & CONNECTION CLEANUP TESTS
# ============================================================================

def test_transaction_rollback_on_error(app):
    """Test that failed transactions roll back and do not commit partial changes."""
    with app.app_context():
        db = get_db()
        # Start a transaction block that fails midway
        try:
            with db:
                db.execute(
                    "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, ?)",
                    ("Rollback Farmer", "+919876543280", "hash_temp", "farmer"),
                )
                # Intentionally trigger an error
                raise RuntimeError("Forced error to test rollback")
        except RuntimeError:
            pass

        # Verify that the insert was rolled back
        user = db.execute(
            "SELECT * FROM users WHERE phone = ?", ("+919876543280",)
        ).fetchone()
        assert user is None


def test_db_connection_cleanup_on_teardown(app):
    """Test that database connection is opened in context and closed on teardown."""
    with app.app_context():
        db = get_db()
        assert db is get_db()  # Reused within same context
        # Connection is open and responsive
        assert db.execute("SELECT 1").fetchone()[0] == 1

    # After exiting app context, close_db was called on teardown.
    # Attempting to execute a query on the old retained connection handle must raise ProgrammingError.
    with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed database"):
        db.execute("SELECT 1")

    # Opening a new context gets a fresh, separate connection
    with app.app_context():
        new_db = get_db()
        assert new_db is not db


def test_test_database_isolation():
    """Verify that separate test app instances have isolated databases."""
    with tempfile.TemporaryDirectory() as dir1, tempfile.TemporaryDirectory() as dir2:
        app1 = create_app({"TESTING": True, "DATABASE": os.path.join(dir1, "app1.db")})
        app2 = create_app({"TESTING": True, "DATABASE": os.path.join(dir2, "app2.db")})

        with app1.app_context():
            init_db()
            insert_user(get_db(), name="Farmer Isolation", phone="+919876543299")
            count1 = get_db().execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
            assert count1 == 1

        with app2.app_context():
            init_db()
            count2 = get_db().execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
            # App 2 must be completely isolated and empty
            assert count2 == 0


# ============================================================================
# 7. ADMIN PROVISIONING CLI TESTS (flask init-admin)
# ============================================================================

def test_init_admin_cli_success(runner, app):
    """Test successful creation of an admin account via init-admin CLI command."""
    password = "SuperSecretPassword123"
    result = runner.invoke(
        args=["init-admin", "--name", "Lab Supervisor", "--phone", "+919876543200"],
        input=f"{password}\n{password}\n",
    )
    assert result.exit_code == 0
    assert "Admin account created successfully" in result.output
    # Ensure neither password nor hash is leaked in output
    assert password not in result.output
    assert "pbkdf2:" not in result.output
    assert "scrypt:" not in result.output

    # Verify record in database
    with app.app_context():
        db = get_db()
        admin = db.execute("SELECT * FROM users WHERE phone = ?", ("+919876543200",)).fetchone()
        assert admin is not None
        assert admin["name"] == "Lab Supervisor"
        assert admin["role"] == "admin"
        # Password must be hashed, not plaintext
        assert admin["password_hash"] != password
        assert check_password_hash(admin["password_hash"], password)


def test_init_admin_cli_rejects_duplicate_admin(runner, app):
    """Test that creating a second admin with the same phone number is rejected."""
    password = "AdminPassword123"
    # First creation succeeds
    result1 = runner.invoke(
        args=["init-admin", "--name", "Admin 1", "--phone", "+919876543202"],
        input=f"{password}\n{password}\n",
    )
    assert result1.exit_code == 0

    # Second creation with identical phone must fail
    result2 = runner.invoke(
        args=["init-admin", "--name", "Admin 2", "--phone", "+919876543202"],
        input=f"{password}\n{password}\n",
    )
    assert result2.exit_code != 0
    assert "already exists" in result2.output.lower()


def test_init_admin_cli_never_promotes_farmer(runner, app):
    """Test that an existing farmer account is never silently promoted to admin."""
    with app.app_context():
        insert_user(get_db(), name="Registered Farmer", phone="+919876543203", role="farmer")

    password = "AdminPassword123"
    result = runner.invoke(
        args=["init-admin", "--name", "Infiltrator", "--phone", "+919876543203"],
        input=f"{password}\n{password}\n",
    )
    assert result.exit_code != 0
    assert "farmer account with this phone number already exists" in result.output.lower()

    # Verify that the farmer account was NOT promoted
    with app.app_context():
        user = get_db().execute("SELECT * FROM users WHERE phone = ?", ("+919876543203",)).fetchone()
        assert user["role"] == "farmer"
        assert user["name"] == "Registered Farmer"


def test_init_admin_cli_rejects_invalid_phone(runner):
    """Test that phone numbers not conforming to E.164 are rejected."""
    password = "AdminPassword123"
    result = runner.invoke(
        args=["init-admin", "--name", "Bad Phone Admin", "--phone", "9876543210"],
        input=f"{password}\n{password}\n",
    )
    assert result.exit_code != 0
    assert "E.164" in result.output


def test_init_admin_cli_rejects_empty_name(runner):
    """Test that empty or whitespace-only admin names are rejected."""
    password = "AdminPassword123"
    result = runner.invoke(
        args=["init-admin", "--name", "   ", "--phone", "+919876543205"],
        input=f"{password}\n{password}\n",
    )
    assert result.exit_code != 0
    assert "Admin name cannot be empty" in result.output


def test_init_admin_cli_rejects_mismatched_password(runner):
    """Test that confirmation password mismatch is rejected."""
    result = runner.invoke(
        args=["init-admin", "--name", "Mismatch Admin", "--phone", "+919876543206"],
        input="Password123\nDifferentPass456\n",
    )
    assert result.exit_code != 0


def test_init_admin_cli_rejects_short_password(runner):
    """Test that passwords shorter than 8 characters are rejected."""
    result = runner.invoke(
        args=["init-admin", "--name", "ShortPass Admin", "--phone", "+919876543207"],
        input="12345\n12345\n",
    )
    assert result.exit_code != 0
    assert "at least 8 characters" in result.output.lower()
