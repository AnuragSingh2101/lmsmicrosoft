import os
import sys

# Ensure project root resolves in sys.path when running this file directly
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(backend_dir)
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from flask import Flask, send_from_directory, redirect, url_for
from flask_cors import CORS
from flask_jwt_extended import JWTManager, unset_jwt_cookies
from dotenv import load_dotenv

load_dotenv()

# Determine directory paths
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(backend_dir)
template_dir = os.path.join(project_dir, "frontend", "templates")
static_dir = os.path.join(project_dir, "frontend", "static")
upload_dir = os.path.join(backend_dir, "uploads")

# Enforce folder creation on startup
os.makedirs(upload_dir, exist_ok=True)
os.makedirs(os.path.join(upload_dir, "thumbnails"), exist_ok=True)
os.makedirs(os.path.join(upload_dir, "notes"), exist_ok=True)
os.makedirs(os.path.join(upload_dir, "submissions"), exist_ok=True)
os.makedirs(os.path.join(upload_dir, "certificates"), exist_ok=True)

# Initialize Flask
app = Flask(
    __name__,
    template_folder=template_dir,
    static_folder=static_dir,
    static_url_path="/static"
)

# Configuration
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev_secret_key_change_me")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt_secret_key_change_me")
app.config["JWT_TOKEN_LOCATION"] = ["cookies", "headers"]
app.config["JWT_COOKIE_CSRF_PROTECT"] = False  # Set to False for local hackathon development
app.config["JWT_COOKIE_SECURE"] = False        # Set to True in HTTPS production environments
app.config["JWT_ACCESS_COOKIE_PATH"] = "/"
app.config["JWT_VERIFY_SUB"] = False
app.config["UPLOAD_FOLDER"] = upload_dir

# Enable Cross-Origin Resource Sharing
CORS(app)

# Initialize JWT Manager
jwt = JWTManager(app)

# --- Global JWT Redirect Exception Handlers ---

@jwt.unauthorized_loader
def unauthorized_callback(callback):
    """
    Redirects user to the login screen if they visit a protected page without a token.
    """
    response = redirect(url_for("views.login_page"))
    unset_jwt_cookies(response)
    return response

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    """
    Redirects user to the login page if their session token expires.
    """
    response = redirect(url_for("views.login_page"))
    unset_jwt_cookies(response)
    return response

@jwt.invalid_token_loader
def invalid_token_callback(error):
    """
    Cleans cookies and redirects if a token is tampered or corrupted.
    """
    response = redirect(url_for("views.login_page"))
    unset_jwt_cookies(response)
    return response

# --- Uploads File Server Route ---

@app.route("/uploads/<path:filename>")
def serve_uploads(filename):
    """
    Serves files from the uploads directory (thumbnails, notes, submissions).
    """
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# --- Register Blueprints ---

from backend.routes.auth import auth_bp
from backend.routes.courses import courses_bp
from backend.routes.assignments import assignments_bp
from backend.routes.quizzes import quizzes_bp
from backend.routes.progress import progress_bp
from backend.routes.chat import chat_bp
from backend.routes.certificates import certificates_bp
from backend.routes.analytics import analytics_bp
from backend.routes.views import views_bp

app.register_blueprint(auth_bp)
app.register_blueprint(courses_bp)
app.register_blueprint(assignments_bp)
app.register_blueprint(quizzes_bp)
app.register_blueprint(progress_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(certificates_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(views_bp)

# Context processor to expose logged_in state in Jinja
@app.context_processor
def inject_auth_state():
    # Since cookies are checked, we can read them manually for basic Jinja template layout checks
    from flask_jwt_extended import decode_token
    from flask import request
    
    token = request.cookies.get("access_token_cookie")
    if token:
        try:
            decoded = decode_token(token)
            identity = decoded["sub"]
            return {"current_user": identity}
        except Exception:
            pass
    return {"current_user": None}

if __name__ == "__main__":
    app.run(debug=False, port=5000)
