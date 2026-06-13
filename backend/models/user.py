from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from backend.utils.db import db, parse_id

users_col = db.users

def create_user(name, email, password, role):
    """
    Creates a new user in the database.
    Returns the user document (without password) or None if email already exists.
    """
    email = email.lower().strip()
    if users_col.find_one({"email": email}):
        return None
    
    hashed_password = generate_password_hash(password)
    user_doc = {
        "name": name.strip(),
        "email": email,
        "password": hashed_password,
        "role": role,  # 'student' or 'teacher'
        "created_at": datetime.utcnow()
    }
    
    result = users_col.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    del user_doc["password"]
    return user_doc

def authenticate_user(email, password):
    """
    Checks user credentials.
    Returns user document (without password) if successful, else None.
    """
    email = email.lower().strip()
    user = users_col.find_one({"email": email})
    if user and check_password_hash(user["password"], password):
        user_copy = dict(user)
        del user_copy["password"]
        return user_copy
    return None

def get_user_by_id(user_id):
    """
    Fetch a user document by ID (safely handles ObjectId conversion).
    Returns None if user does not exist.
    """
    oid = parse_id(user_id)
    if not oid:
        return None
    user = users_col.find_one({"_id": oid})
    if user:
        user_copy = dict(user)
        if "password" in user_copy:
            del user_copy["password"]
        return user_copy
    return None

def get_user_by_email(email):
    """
    Fetch a user document by email.
    """
    return users_col.find_one({"email": email.lower().strip()})
