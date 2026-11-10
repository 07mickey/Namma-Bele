import os
import re
import sqlite3
import click
from flask import current_app, g
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

# E.164 pattern: leading +, non-zero starting country code, 7 to 14 following digits (8-15 digits total)
E164_REGEX = re.compile(r"^\+[1-9]\d{7,14}$")
ALLOWED_STAFF_ROLES = ("operator", "field_worker", "lab_staff", "advisor", "admin")


def get_db():
    """
    Get a database connection for the current application context.
    
    Reuses the connection if it already exists in Flask's `g` object.
    Enforces foreign keys and configures a 5-second busy timeout.
    """
    if "db" not in g:
        db_path = current_app.config["DATABASE"]
        
        # Ensure parent directory exists if using a file path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
            timeout=5.0,
        )
        g.db.row_factory = sqlite3.Row
        
        # Enforce foreign key constraints on every connection
        g.db.execute("PRAGMA foreign_keys = ON;")
        
        # Configure busy timeout
        g.db.execute("PRAGMA busy_timeout = 5000;")

    return g.db


def close_db(e=None):
    """
    Close the database connection at the end of the request/app context.
    """
    db = g.pop("db", None)

    if db is not None:
        db.close()


def migrate_existing_schema(db):
    """
    Applies non-destructive schema migrations to existing SQLite databases.
    Adds new columns to existing tables if they don't already exist.
    """
    # 1. Migrate users table columns
    cursor = db.execute("PRAGMA table_info(users)")
    existing_user_cols = {row["name"] for row in cursor.fetchall()}
    
    if "account_status" not in existing_user_cols:
        db.execute("ALTER TABLE users ADD COLUMN account_status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (account_status IN ('ACTIVE', 'UNCLAIMED', 'SUSPENDED'))")
    if "created_by_user_id" not in existing_user_cols:
        db.execute("ALTER TABLE users ADD COLUMN created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
    if "assigned_lab_id" not in existing_user_cols:
        db.execute("ALTER TABLE users ADD COLUMN assigned_lab_id INTEGER REFERENCES laboratories(id) ON DELETE SET NULL")
    if "preferred_language" not in existing_user_cols:
        db.execute("ALTER TABLE users ADD COLUMN preferred_language TEXT NOT NULL DEFAULT 'en'")

    # 2. Migrate appointments table columns
    cursor = db.execute("PRAGMA table_info(appointments)")
    existing_appt_cols = {row["name"] for row in cursor.fetchall()}
    if "plot_id" not in existing_appt_cols:
        db.execute("ALTER TABLE appointments ADD COLUMN plot_id INTEGER REFERENCES farm_plots(id) ON DELETE SET NULL")
    if "delivery_address_id" not in existing_appt_cols:
        db.execute("ALTER TABLE appointments ADD COLUMN delivery_address_id INTEGER REFERENCES farmer_delivery_addresses(id) ON DELETE SET NULL")

    # 3. Migrate reports table columns
    cursor = db.execute("PRAGMA table_info(reports)")
    existing_rep_cols = {row["name"] for row in cursor.fetchall()}
    if "assay_id" not in existing_rep_cols:
        db.execute("ALTER TABLE reports ADD COLUMN assay_id INTEGER REFERENCES lab_test_assays(id) ON DELETE SET NULL")
    if "authorized_by" not in existing_rep_cols:
        db.execute("ALTER TABLE reports ADD COLUMN authorized_by INTEGER REFERENCES users(id) ON DELETE SET NULL")
    if "authorized_at" not in existing_rep_cols:
        db.execute("ALTER TABLE reports ADD COLUMN authorized_at TEXT")


def seed_reference_data(db):
    """Seeds baseline laboratories if table is empty."""
    lab_count = db.execute("SELECT COUNT(*) AS c FROM laboratories").fetchone()["c"]
    if lab_count == 0:
        db.execute("""
            INSERT OR IGNORE INTO laboratories (id, name, code, district, address, contact_phone)
            VALUES 
            (1, 'District Soil Testing Laboratory, Mandya', 'DSTL-MND-01', 'Mandya', 'Department of Agriculture, Mandya - 571401', '+918232220101'),
            (2, 'Central Soil & Water Testing Lab, Mysuru', 'CSWL-MYS-01', 'Mysuru', 'KRS Road, Industrial Suburb, Mysuru - 570020', '+918212410202'),
            (3, 'Regional Agricultural Research Lab, Bengaluru', 'RARL-BLR-01', 'Bengaluru Rural', 'UAS GKVK Campus, Bellary Road, Bengaluru - 560065', '+918023330153')
        """)
        db.commit()


def init_db():
    """
    Initialize the database using schema.sql and enable WAL mode.
    Also ensures the private reports storage directory is present.
    """
    reports_dir = os.path.join(current_app.instance_path, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    db = get_db()

    # Configure Write-Ahead Logging (WAL) for persistent concurrent performance
    db.execute("PRAGMA journal_mode = WAL;")

    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))

    migrate_existing_schema(db)
    seed_reference_data(db)


@click.command("init-db")
@with_appcontext
def init_db_command():
    """CLI command to initialize the database tables."""
    init_db()
    click.echo("Initialized the database.")


@click.command("init-admin")
@click.option("--name", prompt="Admin Name", help="Full name of administrator")
@click.option("--phone", prompt="Admin Phone (E.164)", help="Phone number in E.164 format (e.g. +919876543200)")
@with_appcontext
def init_admin_command(name, phone):
    """
    Securely provisions an administrator account with hidden interactive password input.
    Never accepts passwords through command-line flags.
    """
    # 1. Validate name
    name_clean = name.strip() if name else ""
    if not name_clean:
        raise click.ClickException("Admin name cannot be empty.")

    # 2. Validate and normalize phone number
    phone_clean = re.sub(r"[\s\-()]", "", phone) if phone else ""
    if not E164_REGEX.match(phone_clean):
        raise click.ClickException("Invalid phone number. Must be in E.164 format (e.g. +919876543200).")

    # 3. Interactive hidden password prompt (never a CLI option)
    password = click.prompt("Admin Password", hide_input=True, confirmation_prompt=True)
    if not password or len(password.strip()) < 8:
        raise click.ClickException("Password must be at least 8 characters long.")

    db = get_db()

    # 4. Check for existing phone number to prevent duplicates or silent promotion
    existing = db.execute("SELECT id, role FROM users WHERE phone = ?", (phone_clean,)).fetchone()
    if existing:
        if existing["role"] == "farmer":
            raise click.ClickException(
                "A farmer account with this phone number already exists. Farmer accounts cannot be promoted to admin."
            )
        raise click.ClickException("An admin account with this phone number already exists.")

    # 5. Hash password and insert record safely
    password_hash = generate_password_hash(password)
    try:
        with db:
            db.execute(
                """
                INSERT INTO users (name, phone, password_hash, role, account_status)
                VALUES (?, ?, ?, 'admin', 'ACTIVE')
                """,
                (name_clean, phone_clean, password_hash),
            )
    except sqlite3.IntegrityError:
        raise click.ClickException("Database integrity error: could not create admin account.")

    # Never output password or password hash
    click.echo(f"Admin account created successfully for {name_clean} ({phone_clean}).")


@click.command("init-staff")
@click.option("--name", prompt="Staff Name", help="Full name of staff member")
@click.option("--phone", prompt="Staff Phone (E.164)", help="Phone number in E.164 format (e.g. +919876543200)")
@click.option("--role", prompt="Staff Role (operator, field_worker, lab_staff, advisor, admin)", help="Role of staff member")
@click.option("--lab-code", default=None, help="Lab code for lab_staff (e.g. DSTL-MND-01)")
@with_appcontext
def init_staff_command(name, phone, role, lab_code):
    """
    Securely provisions an authorized staff account (operator, field_worker, lab_staff, advisor, admin).
    Never allows public self-registration of staff.
    """
    name_clean = name.strip() if name else ""
    if not name_clean:
        raise click.ClickException("Staff name cannot be empty.")

    phone_clean = re.sub(r"[\s\-()]", "", phone) if phone else ""
    if not E164_REGEX.match(phone_clean):
        raise click.ClickException("Invalid phone number. Must be in E.164 format (e.g. +919876543200).")

    role_clean = role.strip() if role else ""
    if role_clean not in ALLOWED_STAFF_ROLES:
        raise click.ClickException(f"Invalid staff role '{role_clean}'. Allowed: {', '.join(ALLOWED_STAFF_ROLES)}.")

    password = click.prompt("Staff Password", hide_input=True, confirmation_prompt=True)
    if not password or len(password.strip()) < 8:
        raise click.ClickException("Password must be at least 8 characters long.")

    db = get_db()
    existing = db.execute("SELECT id, role FROM users WHERE phone = ?", (phone_clean,)).fetchone()
    if existing:
        raise click.ClickException(f"An account with this phone number already exists with role '{existing['role']}'.")

    lab_id = None
    if lab_code:
        lab_row = db.execute("SELECT id FROM laboratories WHERE code = ?", (lab_code.strip(),)).fetchone()
        if not lab_row:
            raise click.ClickException(f"Laboratory with code '{lab_code}' not found.")
        lab_id = lab_row["id"]
    elif role_clean == "lab_staff":
        # Default to first active lab if not specified
        first_lab = db.execute("SELECT id FROM laboratories WHERE is_active = 1 ORDER BY id ASC LIMIT 1").fetchone()
        if first_lab:
            lab_id = first_lab["id"]

    password_hash = generate_password_hash(password)
    try:
        with db:
            db.execute(
                """
                INSERT INTO users (name, phone, password_hash, role, account_status, assigned_lab_id)
                VALUES (?, ?, ?, ?, 'ACTIVE', ?)
                """,
                (name_clean, phone_clean, password_hash, role_clean, lab_id),
            )
    except sqlite3.IntegrityError as err:
        raise click.ClickException(f"Database integrity error: {err}")

    click.echo(f"Staff account created successfully for {name_clean} ({phone_clean}) as '{role_clean}'.")


@click.command("init-demo")
@click.option("--reset/--no-reset", default=True, help="Reset existing demo database")
@with_appcontext
def init_demo_command(reset):
    """Initializes and seeds an isolated demonstration database."""
    from scripts.seed_demo_data import seed_demo_database, DEMO_DB_PATH, DEMO_REPORTS_DIR
    seed_demo_database(db_path=DEMO_DB_PATH, reports_dir=DEMO_REPORTS_DIR, reset=reset)
    click.echo(f"Initialized demo database at {DEMO_DB_PATH}.")


def init_app(app):
    """
    Register database functions with the Flask application instance.
    - Registers close_db with teardown_appcontext.
    - Adds the 'init-db' CLI command.
    - Adds the 'init-admin' CLI command.
    - Adds the 'init-staff' CLI command.
    - Adds the 'init-demo' CLI command.
    """
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(init_admin_command)
    app.cli.add_command(init_staff_command)
    app.cli.add_command(init_demo_command)
