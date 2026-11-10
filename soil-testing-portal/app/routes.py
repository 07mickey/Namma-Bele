from flask import Blueprint, jsonify

api_bp = Blueprint("api", __name__)


@api_bp.route("/api/health", methods=["GET"])
def health_check():
    """
    Health check endpoint to verify that the backend server is running.
    
    Returns:
        JSON response with status and confirmation message.
    """
    return jsonify({
        "status": "healthy",
        "message": "Soil Testing Portal backend is running"
    }), 200

