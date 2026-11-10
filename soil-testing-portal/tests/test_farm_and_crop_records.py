import os
import sys
import tempfile
import pytest
from werkzeug.security import generate_password_hash

# Ensure soil-testing-portal directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.db import get_db, init_db


@pytest.fixture
def app_and_db():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_farm_records.db")
        app = create_app({
            "TESTING": True,
            "DATABASE": db_path,
            "SECRET_KEY": "test-farm-key",
        })
        with app.app_context():
            init_db()
        yield app, db_path


@pytest.fixture
def app(app_and_db):
    app, _ = app_and_db
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def get_csrf(client):
    res = client.get("/api/auth/csrf-token")
    assert res.status_code == 200
    return res.get_json()["csrf_token"]


def create_user(app, name, phone, role="farmer"):
    with app.app_context():
        db = get_db()
        cur = db.execute(
            "INSERT INTO users (name, phone, password_hash, role) VALUES (?, ?, ?, ?)",
            (name, phone, generate_password_hash("Password123"), role),
        )
        db.commit()
        return cur.lastrowid


def login(client, phone):
    csrf = get_csrf(client)
    res = client.post(
        "/api/auth/login",
        json={"phone": phone, "password": "Password123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    return get_csrf(client)


# ============================================================================
# FARM & CROP RECORDS TESTS
# ============================================================================

def test_farm_plots_crud(client, app):
    """Test creating, reading, updating and deleting farm plots."""
    create_user(app, "Farmer Plots", "+919876543401", role="farmer")
    csrf = login(client, "+919876543401")

    # 1. Create plot
    payload = {
        "plot_name": "East Wetland Plot",
        "survey_number": "SY-44/1",
        "area": 4.5,
        "area_unit": "Acres",
        "soil_type": "Clayey Loam",
        "irrigation_source": "Canal",
        "landmark": "Near Gram Panchayat office",
        "taluk": "Pandavapura",
        "district": "Mandya",
    }
    res_create = client.post("/api/farm/plots", json=payload, headers={"X-CSRF-Token": csrf})
    assert res_create.status_code == 201
    plot_id = res_create.get_json()["plot"]["id"]

    # 2. List plots
    res_list = client.get("/api/farm/plots")
    assert res_list.status_code == 200
    plots = res_list.get_json()["plots"]
    assert len(plots) == 1
    assert plots[0]["plot_name"] == "East Wetland Plot"
    assert plots[0]["survey_number"] == "SY-44/1"

    # 3. Update plot
    res_update = client.put(
        f"/api/farm/plots/{plot_id}",
        json={"plot_name": "East Wetland Plot (Renamed)", "area": 5.0},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_update.status_code == 200

    # 4. Delete plot
    res_delete = client.delete(f"/api/farm/plots/{plot_id}", headers={"X-CSRF-Token": csrf})
    assert res_delete.status_code == 200
    res_list_after = client.get("/api/farm/plots")
    assert len(res_list_after.get_json()["plots"]) == 0


def test_crop_records_and_paddy_standardization(client, app):
    """Test crop record creation and standardized 'Paddy / Rice' naming."""
    create_user(app, "Farmer Crop", "+919876543402", role="farmer")
    csrf = login(client, "+919876543402")

    # Create plot first
    res_plot = client.post(
        "/api/farm/plots",
        json={"plot_name": "Main Field", "survey_number": "SY-12", "area": 3.0},
        headers={"X-CSRF-Token": csrf},
    )
    plot_id = res_plot.get_json()["plot"]["id"]

    # 1. Test input 'paddy' gets standardized to 'Paddy / Rice'
    crop_payload1 = {
        "plot_id": plot_id,
        "crop_name": "paddy",
        "variety": "Jyothi (IR-579)",
        "year": 2026,
        "season": "Kharif",
        "sowing_date": "2026-06-15",
        "harvest_date": "2026-10-20",
    }
    res_crop1 = client.post("/api/farm/crops", json=crop_payload1, headers={"X-CSRF-Token": csrf})
    assert res_crop1.status_code == 201
    assert res_crop1.get_json()["crop_name"] == "Paddy / Rice"

    # 2. Test input 'Rice' also gets standardized to 'Paddy / Rice'
    crop_payload2 = {
        "plot_id": plot_id,
        "crop_name": "Rice",
        "variety": "BPT-5204 (Sona Masuri)",
        "year": 2026,
        "season": "Rabi",
    }
    res_crop2 = client.post("/api/farm/crops", json=crop_payload2, headers={"X-CSRF-Token": csrf})
    assert res_crop2.status_code == 201
    assert res_crop2.get_json()["crop_name"] == "Paddy / Rice"

    # 3. Test other crops remain unchanged
    crop_payload3 = {
        "plot_id": plot_id,
        "crop_name": "Sugarcane",
        "variety": "Co 86032",
        "year": 2026,
        "season": "Perennial",
    }
    res_crop3 = client.post("/api/farm/crops", json=crop_payload3, headers={"X-CSRF-Token": csrf})
    assert res_crop3.status_code == 201
    assert res_crop3.get_json()["crop_name"] == "Sugarcane"


def test_harvest_and_sales_revenue_validations(client, app):
    """
    1. Log harvest yield (e.g. 50 Quintals).
    2. Attempt sale exceeding harvested quantity -> HTTP 400 VALIDATION_ERROR.
    3. Log valid sale (30 Quintals @ ₹2,200/Quintal) -> Gross Revenue = ₹66,000.
    4. Verify remaining stock is 20 Quintals.
    5. Verify summary metrics.
    """
    create_user(app, "Farmer Harvest Sales", "+919876543403", role="farmer")
    csrf = login(client, "+919876543403")

    # Create plot and crop
    res_plot = client.post(
        "/api/farm/plots",
        json={"plot_name": "Paddy Field A", "survey_number": "SY-99", "area": 2.5},
        headers={"X-CSRF-Token": csrf},
    )
    plot_id = res_plot.get_json()["plot"]["id"]

    res_crop = client.post(
        "/api/farm/crops",
        json={"plot_id": plot_id, "crop_name": "Paddy / Rice", "variety": "Sona Masuri", "year": 2026, "season": "Kharif"},
        headers={"X-CSRF-Token": csrf},
    )
    crop_id = res_crop.get_json()["crop_id"]

    # 1. Log harvest of 50.0 Quintals
    res_harvest = client.post(
        "/api/farm/harvests",
        json={
            "crop_record_id": crop_id,
            "harvest_date": "2026-10-15",
            "total_quantity": 50.0,
            "quantity_unit": "Quintals",
            "quality_grade": "Grade A",
            "storage_location": "Main Farm Warehouse",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res_harvest.status_code == 201

    # 2. Attempt sale of 65.0 Quintals (exceeds 50.0 available) -> MUST FAIL
    res_oversell = client.post(
        "/api/farm/sales",
        json={
            "crop_record_id": crop_id,
            "sale_date": "2026-10-25",
            "quantity_sold": 65.0,
            "price_per_unit": 2200.0,
            "buyer_market": "APMC Mandi Mandya",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res_oversell.status_code == 400
    assert res_oversell.get_json()["error"]["code"] == "VALIDATION_ERROR"
    assert "exceeds available stock" in res_oversell.get_json()["error"]["message"]

    # 3. Log valid sale of 30.0 Quintals at ₹2,200/Quintal
    res_sale = client.post(
        "/api/farm/sales",
        json={
            "crop_record_id": crop_id,
            "sale_date": "2026-10-25",
            "quantity_sold": 30.0,
            "price_per_unit": 2200.0,
            "buyer_market": "APMC Mandi Mandya",
            "payment_status": "Received",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res_sale.status_code == 201
    sale_data = res_sale.get_json()
    assert sale_data["gross_revenue"] == 66000.0
    assert sale_data["remaining_stock"] == 20.0

    # 4. Check farm summary
    res_sum = client.get("/api/farm/summary")
    assert res_sum.status_code == 200
    summary = res_sum.get_json()
    assert summary["total_plots"] == 1
    assert summary["active_crops_count"] == 1
    assert summary["total_harvested_quantity"] == 50.0
    assert summary["total_sold_quantity"] == 30.0
    assert summary["remaining_stock"] == 20.0
    assert summary["total_gross_revenue"] == 66000.0

