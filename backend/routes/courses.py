import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from backend.models.course import (
    create_course, update_course, delete_course, get_course_by_id,
    get_all_courses, get_courses_by_teacher, create_lesson, update_lesson,
    delete_lesson, get_lessons_by_course, get_lesson_by_id
)
from backend.models.progress import enroll_student_in_course, get_or_create_progress, get_student_enrollments
from backend.utils.db import to_json, to_json_list

courses_bp = Blueprint("courses", __name__)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
ALLOWED_PDF_EXTENSIONS = {"pdf"}

def allowed_file(filename, extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions

def save_uploaded_file(file, folder_name, allowed_extensions):
    """
    Saves an uploaded file to a subfolder of current_app.config['UPLOAD_FOLDER'].
    Returns the relative web path (e.g. 'uploads/thumbnails/xyz.png') or None.
    """
    if not file or file.filename == "":
        return None
        
    if not allowed_file(file.filename, allowed_extensions):
        return None
        
    # Generate a unique secure filename
    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    
    upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"], folder_name)
    os.makedirs(upload_path, exist_ok=True)
    
    file.save(os.path.join(upload_path, unique_name))
    return f"uploads/{folder_name}/{unique_name}"

# --- Course Routes ---

@courses_bp.route("/api/courses", methods=["GET"])
def list_courses():
    category = request.args.get("category")
    courses = get_all_courses(category)
    return jsonify(to_json_list(courses))

@courses_bp.route("/api/courses/teacher", methods=["GET"])
@jwt_required()
def list_teacher_courses():
    identity = get_jwt_identity()
    if identity["role"] != "teacher":
        return jsonify({"error": "Unauthorized"}), 403
        
    courses = get_courses_by_teacher(identity["id"])
    return jsonify(to_json_list(courses))

@courses_bp.route("/api/courses", methods=["POST"])
@jwt_required()
def add_course():
    identity = get_jwt_identity()
    if identity["role"] != "teacher":
        return jsonify({"error": "Only teachers can create courses"}), 403
        
    title = request.form.get("title")
    description = request.form.get("description")
    category = request.form.get("category")
    
    if not title or not description or not category:
        return jsonify({"error": "Missing title, description, or category"}), 400
        
    thumbnail_file = request.files.get("thumbnail")
    thumbnail_path = "static/images/course-placeholder.jpg"  # default fallback
    
    if thumbnail_file:
        saved_path = save_uploaded_file(thumbnail_file, "thumbnails", ALLOWED_IMAGE_EXTENSIONS)
        if saved_path:
            thumbnail_path = saved_path
            
    course = create_course(title, description, category, thumbnail_path, identity["id"])
    return jsonify({"message": "Course created successfully", "course": to_json(course)}), 201

@courses_bp.route("/api/courses/<course_id>", methods=["GET"])
def get_course(course_id):
    course = get_course_by_id(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
    return jsonify(to_json(course))

@courses_bp.route("/api/courses/<course_id>", methods=["PUT"])
@jwt_required()
def edit_course(course_id):
    identity = get_jwt_identity()
    course = get_course_by_id(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
        
    # Check ownership
    if str(course["teacher_id"]) != identity["id"]:
        return jsonify({"error": "Unauthorized"}), 403
        
    title = request.form.get("title")
    description = request.form.get("description")
    category = request.form.get("category")
    
    if not title or not description or not category:
        return jsonify({"error": "Missing required fields"}), 400
        
    thumbnail_file = request.files.get("thumbnail")
    thumbnail_path = None
    if thumbnail_file:
        thumbnail_path = save_uploaded_file(thumbnail_file, "thumbnails", ALLOWED_IMAGE_EXTENSIONS)
        
    updated = update_course(course_id, title, description, category, thumbnail_path)
    return jsonify({"message": "Course updated successfully", "course": to_json(updated)})

@courses_bp.route("/api/courses/<course_id>", methods=["DELETE"])
@jwt_required()
def remove_course(course_id):
    identity = get_jwt_identity()
    course = get_course_by_id(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
        
    # Check ownership
    if str(course["teacher_id"]) != identity["id"]:
        return jsonify({"error": "Unauthorized"}), 403
        
    delete_course(course_id)
    return jsonify({"message": "Course deleted successfully"})

@courses_bp.route("/api/courses/<course_id>/enroll", methods=["POST"])
@jwt_required()
def enroll(course_id):
    identity = get_jwt_identity()
    if identity["role"] != "student":
        return jsonify({"error": "Only students can enroll in courses"}), 403
        
    progress = enroll_student_in_course(identity["id"], course_id)
    return jsonify({"message": "Enrolled successfully", "progress": to_json(progress)})

@courses_bp.route("/api/courses/enrolled", methods=["GET"])
@jwt_required()
def list_enrolled_courses():
    identity = get_jwt_identity()
    if identity["role"] != "student":
        return jsonify({"error": "Unauthorized"}), 403
        
    enrollments = get_student_enrollments(identity["id"])
    return jsonify(to_json_list(enrollments))

# --- Lesson Routes ---

@courses_bp.route("/api/courses/<course_id>/lessons", methods=["GET"])
def list_lessons(course_id):
    lessons = get_lessons_by_course(course_id)
    return jsonify(to_json_list(lessons))

@courses_bp.route("/api/courses/<course_id>/lessons", methods=["POST"])
@jwt_required()
def add_lesson(course_id):
    identity = get_jwt_identity()
    course = current_course = get_course_by_id(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
        
    if str(course["teacher_id"]) != identity["id"]:
        return jsonify({"error": "Unauthorized"}), 403
        
    title = request.form.get("title")
    description = request.form.get("description")
    youtube_id = request.form.get("youtube_id", "")
    duration = request.form.get("duration", 0)
    
    if not title or not description:
        return jsonify({"error": "Missing title or description"}), 400
        
    notes_file = request.files.get("notes")
    notes_path = ""
    if notes_file:
        notes_path = save_uploaded_file(notes_file, "notes", ALLOWED_PDF_EXTENSIONS) or ""
        
    lesson = create_lesson(course_id, title, description, youtube_id, notes_path, duration)
    return jsonify({"message": "Lesson added successfully", "lesson": to_json(lesson)}), 201

@courses_bp.route("/api/lessons/<lesson_id>", methods=["PUT"])
@jwt_required()
def edit_lesson(lesson_id):
    identity = get_jwt_identity()
    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        return jsonify({"error": "Lesson not found"}), 404
        
    course = get_course_by_id(lesson["course_id"])
    if str(course["teacher_id"]) != identity["id"]:
        return jsonify({"error": "Unauthorized"}), 403
        
    title = request.form.get("title")
    description = request.form.get("description")
    youtube_id = request.form.get("youtube_id")
    duration = request.form.get("duration")
    
    if not title or not description:
        return jsonify({"error": "Missing title or description"}), 400
        
    notes_file = request.files.get("notes")
    notes_path = None
    if notes_file:
        notes_path = save_uploaded_file(notes_file, "notes", ALLOWED_PDF_EXTENSIONS)
        
    updated = update_lesson(lesson_id, title, description, youtube_id, notes_path, duration)
    return jsonify({"message": "Lesson updated successfully", "lesson": to_json(updated)})

@courses_bp.route("/api/lessons/<lesson_id>", methods=["DELETE"])
@jwt_required()
def remove_lesson(lesson_id):
    identity = get_jwt_identity()
    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        return jsonify({"error": "Lesson not found"}), 404
        
    course = get_course_by_id(lesson["course_id"])
    if str(course["teacher_id"]) != identity["id"]:
        return jsonify({"error": "Unauthorized"}), 403
        
    delete_lesson(lesson_id)
    return jsonify({"message": "Lesson deleted successfully"})
