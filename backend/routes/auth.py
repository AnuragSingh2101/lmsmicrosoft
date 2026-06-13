from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity,
    set_access_cookies, unset_jwt_cookies
)
from backend.models.user import create_user, authenticate_user, get_user_by_id

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    """
    Registers a new user (student or teacher).
    """
    data = request.get_json() or {}
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "student")  # default to student
    
    if not name or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400
        
    if role not in ["student", "teacher"]:
        return jsonify({"error": "Invalid role selected"}), 400
        
    user = create_user(name, email, password, role)
    if not user:
        return jsonify({"error": "User with this email already exists"}), 400
        
    return jsonify({
        "message": "User registered successfully",
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }), 201

@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    """
    Authenticates a user and sets the JWT token as an HTTPOnly cookie.
    """
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400
        
    user = authenticate_user(email, password)
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401
        
    # Create the access token
    identity = {"id": str(user["_id"]), "role": user["role"], "name": user["name"]}
    access_token = create_access_token(identity=identity)
    
    response = jsonify({
        "message": "Login successful",
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    })
    
    # Store token in cookie
    set_access_cookies(response, access_token)
    return response

@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    """
    Unsets the JWT cookies to log out the user.
    """
    response = jsonify({"message": "Logout successful"})
    unset_jwt_cookies(response)
    return response

@auth_bp.route("/api/auth/profile", methods=["GET"])
@jwt_required()
def profile():
    """
    Returns the current user's profile details.
    """
    identity = get_jwt_identity()
    user = get_user_by_id(identity["id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    return jsonify({
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    })
