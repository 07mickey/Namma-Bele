import hashlib
import re
import secrets
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import Blueprint, current_app, g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import get_db

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Standard E.164 format regex: + followed by 1-9, then 7 to 14 digits (8-15 digits total)
E164_REGEX = re.compile(r"^\+[1-9]\d{7,14}$")


# ============================================================================
# HELPER FUNCTIONS & ERROR FORMATTING
# ============================================================================

def error_response(code, message, status_code, details=None):
    """Generates a standardized JSON error response."""
    payload = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        payload["error"]["details"] = details
    return jsonify(payload), status_code


def normalize_phone(phone_str):
    """Strips whitespace, hyphens, and formatting characters from a phone number."""
    if not phone_str or not isinstance(phone_str, str):
        return ""
    return re.sub(r"[\s\-()]", "", phone_str)


def generate_csrf_token():
    """Generates a cryptographically strong CSRF token and binds it to the session."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


# ============================================================================
# CSRF PROTECTION HOOK
# ============================================================================

def verify_csrf_token():
    """
    Validates CSRF token on state-changing requests (POST, PUT, PATCH, DELETE).
    Safe HTTP methods (GET, HEAD, OPTIONS) and public health check are exempt.
    """
    if request.path == "/api/health":
        return None

    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        # Ensure session exists and has a token
        expected_token = session.get("csrf_token")
        
        # Check X-CSRF-Token header first, then JSON body, then form data
        provided_token = request.headers.get("X-CSRF-Token")
        if not provided_token and request.is_json:
            provided_token = request.get_json(silent=True, cache=True).get("_csrf_token") if request.get_json(silent=True) else None
        if not provided_token and request.form:
            provided_token = request.form.get("_csrf_token")

        if not expected_token or not provided_token or not secrets.compare_digest(expected_token, provided_token):
            return error_response(
                code="CSRF_ERROR",
                message="CSRF token missing or invalid. Please refresh the page.",
                status_code=403,
            )
    return None


# ============================================================================
# AUTHORIZATION DECORATORS
# ============================================================================

def get_current_user():
    """
    Retrieves the current authenticated user from the database.
    Reloads the user role from SQLite to prevent stale session permissions.
    """
    if "current_user" not in g:
        user_id = session.get("user_id")
        if not user_id:
            g.current_user = None
            return None

        db = get_db()
        user = db.execute(
            "SELECT id, name, phone, role, account_status, preferred_language, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if user is None:
            # Stale session referencing a deleted or non-existent user
            session.clear()
            g.current_user = None
            return None

        g.current_user = user

    return g.current_user


def login_required(f):
    """Decorator that requires an authenticated user session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return error_response(
                code="UNAUTHENTICATED",
                message="Authentication required.",
                status_code=401,
            )
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator that requires an authenticated user whose database role is 'admin'.
    Never trusts client-supplied roles.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return error_response(
                code="UNAUTHENTICATED",
                message="Authentication required.",
                status_code=401,
            )
        if user["role"] != "admin":
            return error_response(
                code="FORBIDDEN",
                message="Admin privileges required.",
                status_code=403,
            )
        return f(*args, **kwargs)
    return decorated_function


def farmer_required(f):
    """
    Decorator that requires an authenticated user whose database role is 'farmer'.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return error_response(
                code="UNAUTHENTICATED",
                message="Authentication required.",
                status_code=401,
            )
        if user["role"] != "farmer":
            return error_response(
                code="FORBIDDEN",
                message="Farmer privileges required.",
                status_code=403,
            )
        return f(*args, **kwargs)
    return decorated_function


def operator_required(f):
    """
    Decorator that requires an authenticated user whose role is 'operator' or 'admin'.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return error_response(
                code="UNAUTHENTICATED",
                message="Authentication required.",
                status_code=401,
            )
        if user["role"] not in ("operator", "admin"):
            return error_response(
                code="FORBIDDEN",
                message="Operator privileges required.",
                status_code=403,
            )
        return f(*args, **kwargs)
    return decorated_function


def field_worker_required(f):
    """
    Decorator that requires an authenticated user whose role is 'field_worker' or 'admin'.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return error_response(
                code="UNAUTHENTICATED",
                message="Authentication required.",
                status_code=401,
            )
        if user["role"] not in ("field_worker", "admin"):
            return error_response(
                code="FORBIDDEN",
                message="Field worker privileges required.",
                status_code=403,
            )
        return f(*args, **kwargs)
    return decorated_function


def lab_staff_required(f):
    """
    Decorator that requires an authenticated user whose role is 'lab_staff' or 'admin'.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return error_response(
                code="UNAUTHENTICATED",
                message="Authentication required.",
                status_code=401,
            )
        if user["role"] not in ("lab_staff", "admin"):
            return error_response(
                code="FORBIDDEN",
                message="Laboratory staff privileges required.",
                status_code=403,
            )
        return f(*args, **kwargs)
    return decorated_function


def advisor_required(f):
    """
    Decorator that requires an authenticated user whose role is 'advisor' or 'admin'.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return error_response(
                code="UNAUTHENTICATED",
                message="Authentication required.",
                status_code=401,
            )
        if user["role"] not in ("advisor", "admin"):
            return error_response(
                code="FORBIDDEN",
                message="Agricultural advisor privileges required.",
                status_code=403,
            )
        return f(*args, **kwargs)
    return decorated_function


def staff_required(f):
    """
    Decorator that requires any authorized staff role.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return error_response(
                code="UNAUTHENTICATED",
                message="Authentication required.",
                status_code=401,
            )
        if user["role"] not in ("admin", "operator", "field_worker", "lab_staff", "advisor"):
            return error_response(
                code="FORBIDDEN",
                message="Staff privileges required.",
                status_code=403,
            )
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@auth_bp.route("/csrf-token", methods=["GET"])
def get_csrf():
    """
    Returns the CSRF token for the current session.
    Clients call this upon initial page load or session establishment.
    """
    token = generate_csrf_token()
    return jsonify({
        "status": "success",
        "csrf_token": token
    }), 200


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Registers a new farmer account.
    - Public registration strictly assigns role='farmer'.
    - Validates name, E.164 phone number, and password policy.
    - Prevents duplicate phone registration.
    - Plaintext passwords are never stored.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return error_response(
            code="MALFORMED_REQUEST",
            message="Request body must be a valid JSON object.",
            status_code=400,
        )

    # 1. Validate Name
    name = data.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        return error_response(
            code="VALIDATION_ERROR",
            message="Name is required and cannot be empty.",
            status_code=400,
            details={"field": "name"},
        )
    clean_name = name.strip()

    # 2. Validate & Normalize Phone
    raw_phone = data.get("phone")
    clean_phone = normalize_phone(raw_phone)
    if not clean_phone or not E164_REGEX.match(clean_phone):
        return error_response(
            code="VALIDATION_ERROR",
            message="Invalid phone number. Must be in standard E.164 format (e.g. +919876543210).",
            status_code=400,
            details={"field": "phone"},
        )

    # 3. Validate Password Policy (minimum 8 characters)
    password = data.get("password")
    if not password or not isinstance(password, str) or len(password.strip()) < 8:
        return error_response(
            code="VALIDATION_ERROR",
            message="Password is required and must be at least 8 characters long.",
            status_code=400,
            details={"field": "password"},
        )

    db = get_db()

    # 4. Check for existing phone number to prevent duplicates
    existing_user = db.execute(
        "SELECT id FROM users WHERE phone = ?",
        (clean_phone,),
    ).fetchone()

    if existing_user:
        return error_response(
            code="CONFLICT",
            message="An account with this phone number already exists.",
            status_code=409,
            details={"field": "phone"},
        )

    # 5. Hash password and insert user with hardcoded role='farmer'
    # Any client-supplied 'role' in data is completely ignored
    password_hash = generate_password_hash(password)

    with db:
        cursor = db.execute(
            """
            INSERT INTO users (name, phone, password_hash, role, account_status)
            VALUES (?, ?, ?, 'farmer', 'ACTIVE')
            """,
            (clean_name, clean_phone, password_hash),
        )
        user_id = cursor.lastrowid

    return jsonify({
        "status": "success",
        "message": "Account created successfully. Please log in.",
        "user": {
            "id": user_id,
            "name": clean_name,
            "phone": clean_phone,
            "role": "farmer",
        }
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticates a user via phone number and password.
    - Clears any previous session state.
    - Stores minimal identity (user_id) in the signed session cookie.
    - Generates a fresh CSRF token to prevent session fixation.
    - Returns generic error message for invalid credentials.
    - Blocks unclaimed or suspended accounts.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return error_response(
            code="MALFORMED_REQUEST",
            message="Request body must be a valid JSON object.",
            status_code=400,
        )

    raw_phone = data.get("phone")
    password = data.get("password")

    if not raw_phone or not isinstance(raw_phone, str) or not password or not isinstance(password, str):
        return error_response(
            code="VALIDATION_ERROR",
            message="Phone number and password are required.",
            status_code=400,
        )

    clean_phone = normalize_phone(raw_phone)
    if not clean_phone or not E164_REGEX.match(clean_phone):
        return error_response(
            code="INVALID_CREDENTIALS",
            message="Invalid phone number or password.",
            status_code=401,
        )

    db = get_db()
    user = db.execute(
        "SELECT id, name, phone, password_hash, role, account_status FROM users WHERE phone = ?",
        (clean_phone,),
    ).fetchone()

    # Generic invalid-credentials response prevents account enumeration
    if user is None:
        return error_response(
            code="INVALID_CREDENTIALS",
            message="Invalid phone number or password.",
            status_code=401,
        )

    # Block unclaimed assisted-registration accounts from password login
    if user["account_status"] == "UNCLAIMED":
        return error_response(
            code="ACCOUNT_UNCLAIMED",
            message="This account was registered through assisted service and has not yet been activated online. Please activate your account first.",
            status_code=403,
        )

    if user["account_status"] == "SUSPENDED":
        return error_response(
            code="ACCOUNT_SUSPENDED",
            message="This account has been suspended. Please contact the agricultural office.",
            status_code=403,
        )

    if not check_password_hash(user["password_hash"], password):
        return error_response(
            code="INVALID_CREDENTIALS",
            message="Invalid phone number or password.",
            status_code=401,
        )

    # Authentication successful: establish session
    session.clear()
    session["user_id"] = user["id"]
    # Generate fresh CSRF token for the authenticated session
    session["csrf_token"] = secrets.token_hex(32)

    return jsonify({
        "status": "success",
        "message": "Login successful.",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "phone": user["phone"],
            "role": user["role"],
        }
    }), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """
    Clears the current session and invalidates session credentials.
    Safe to call even if the user is already logged out.
    """
    session.clear()
    return jsonify({
        "status": "success",
        "message": "Successfully logged out."
    }), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    """
    Returns identity and role information for the currently authenticated user.
    Role is always reloaded from the database.
    Returns authenticated=False if unauthenticated or session is stale.
    """
    user = get_current_user()

    if user is None:
        return jsonify({
            "authenticated": False,
            "user": None
        }), 200

    return jsonify({
        "authenticated": True,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "phone": user["phone"],
            "role": user["role"],
            "account_status": user["account_status"],
            "preferred_language": user["preferred_language"],
        }
    }), 200


# ============================================================================
# ACCOUNT ACTIVATION (CLAIM) FOR ASSISTED REGISTRATIONS
# ============================================================================

@auth_bp.route("/claim/initiate", methods=["POST"])
def claim_initiate():
    """
    Initiates account activation for a farmer registered via assisted service.
    Generates a secure 6-digit OTP and claim token with 15-minute expiry.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return error_response(
            code="MALFORMED_REQUEST",
            message="Request body must be a valid JSON object.",
            status_code=400,
        )

    raw_phone = data.get("phone")
    clean_phone = normalize_phone(raw_phone)
    if not clean_phone or not E164_REGEX.match(clean_phone):
        return error_response(
            code="VALIDATION_ERROR",
            message="A valid phone number in E.164 format is required.",
            status_code=400,
            details={"field": "phone"},
        )

    db = get_db()
    user = db.execute(
        "SELECT id, name, phone, account_status FROM users WHERE phone = ?",
        (clean_phone,),
    ).fetchone()

    if not user:
        return error_response(
            code="NOT_FOUND",
            message="No account found registered with this phone number.",
            status_code=404,
        )

    if user["account_status"] == "ACTIVE":
        return error_response(
            code="ACCOUNT_ALREADY_ACTIVE",
            message="This account is already active. You can log in directly with your password.",
            status_code=400,
        )

    # Generate 6-digit OTP and secure claim token
    otp = str(secrets.randbelow(900000) + 100000)
    claim_token = secrets.token_hex(32)

    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    claim_token_hash = hashlib.sha256(claim_token.encode("utf-8")).hexdigest()

    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")

    with db:
        # Replace any existing activation record for this farmer
        db.execute(
            """
            INSERT OR REPLACE INTO farmer_account_activations (farmer_id, claim_token_hash, otp_hash, expires_at, attempts_remaining)
            VALUES (?, ?, ?, ?, 5)
            """,
            (user["id"], claim_token_hash, otp_hash, expires_at),
        )

    if current_app.config.get("FLASK_ENV") == "production":
        current_app.logger.info(f"[SMS GATEWAY] Verification OTP dispatched to {clean_phone} (content hidden in production)")
    else:
        current_app.logger.info(f"[SMS GATEWAY MOCK] Verification OTP for {clean_phone}: {otp}")

    response_payload = {
        "status": "success",
        "message": "Activation code sent via SMS. Please enter the OTP to set your password.",
        "claim_token": claim_token,
    }
    # In test environments, provide otp_preview for programmatic verification
    if current_app.config.get("TESTING"):
        response_payload["otp_preview"] = otp

    return jsonify(response_payload), 200


@auth_bp.route("/claim/complete", methods=["POST"])
def claim_complete():
    """
    Verifies activation OTP and claim token, setting the farmer's online password
    and activating their account.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return error_response(
            code="MALFORMED_REQUEST",
            message="Request body must be a valid JSON object.",
            status_code=400,
        )

    raw_phone = data.get("phone")
    claim_token = data.get("claim_token")
    otp = data.get("otp")
    new_password = data.get("password")

    clean_phone = normalize_phone(raw_phone)
    if not clean_phone or not E164_REGEX.match(clean_phone):
        return error_response(
            code="VALIDATION_ERROR",
            message="Invalid phone number.",
            status_code=400,
            details={"field": "phone"},
        )

    if not claim_token or not isinstance(claim_token, str):
        return error_response(
            code="VALIDATION_ERROR",
            message="Claim token is required.",
            status_code=400,
            details={"field": "claim_token"},
        )

    if not otp or not isinstance(otp, str) or not otp.strip().isdigit() or len(otp.strip()) != 6:
        return error_response(
            code="VALIDATION_ERROR",
            message="A 6-digit OTP code is required.",
            status_code=400,
            details={"field": "otp"},
        )

    if not new_password or not isinstance(new_password, str) or len(new_password.strip()) < 8:
        return error_response(
            code="VALIDATION_ERROR",
            message="Password must be at least 8 characters long.",
            status_code=400,
            details={"field": "password"},
        )

    db = get_db()
    user = db.execute(
        "SELECT id, name, phone, account_status FROM users WHERE phone = ?",
        (clean_phone,),
    ).fetchone()

    if not user:
        return error_response(
            code="NOT_FOUND",
            message="Account not found.",
            status_code=404,
        )

    activation = db.execute(
        "SELECT * FROM farmer_account_activations WHERE farmer_id = ?",
        (user["id"],),
    ).fetchone()

    if not activation:
        return error_response(
            code="ACTIVATION_EXPIRED",
            message="No active activation request found. Please request a new activation code.",
            status_code=400,
        )

    # Check attempts remaining
    if activation["attempts_remaining"] <= 0:
        with db:
            db.execute("DELETE FROM farmer_account_activations WHERE farmer_id = ?", (user["id"],))
        return error_response(
            code="ATTEMPTS_EXHAUSTED",
            message="Maximum verification attempts exceeded. Please request a new activation code.",
            status_code=400,
        )

    # Verify claim_token
    token_hash = hashlib.sha256(claim_token.strip().encode("utf-8")).hexdigest()
    if not secrets.compare_digest(token_hash, activation["claim_token_hash"]):
        return error_response(
            code="INVALID_CLAIM_TOKEN",
            message="Invalid activation session token.",
            status_code=400,
        )

    # Verify OTP
    input_otp_hash = hashlib.sha256(otp.strip().encode("utf-8")).hexdigest()
    if not secrets.compare_digest(input_otp_hash, activation["otp_hash"]):
        with db:
            db.execute(
                "UPDATE farmer_account_activations SET attempts_remaining = attempts_remaining - 1 WHERE farmer_id = ?",
                (user["id"],),
            )
        return error_response(
            code="INVALID_OTP",
            message="Incorrect verification code. Please check your SMS and try again.",
            status_code=400,
        )

    # Activation successful: set password, activate account, delete activation record
    new_password_hash = generate_password_hash(new_password.strip())
    with db:
        db.execute(
            """
            UPDATE users 
            SET password_hash = ?, account_status = 'ACTIVE'
            WHERE id = ?
            """,
            (new_password_hash, user["id"]),
        )
        db.execute("DELETE FROM farmer_account_activations WHERE farmer_id = ?", (user["id"],))

    return jsonify({
        "status": "success",
        "message": "Account activated successfully. You can now log in with your new password.",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "phone": clean_phone,
        }
    }), 200
