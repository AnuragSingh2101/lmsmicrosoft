from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models.progress import (
    complete_lesson, watch_video, update_learning_time, get_or_create_progress, get_course_progress_percentage
)
from backend.utils.db import to_json

progress_bp = Blueprint("progress", __name__)

@progress_bp.route("/api/courses/<course_id>/progress", methods=["GET"])
@jwt_required()
def get_progress(course_id):
    """
    Fetches the logged-in student's progress in a course.
    """
    identity = get_jwt_identity()
    if identity["role"] != "student":
        return jsonify({"error": "Unauthorized"}), 403
        
    progress = get_or_create_progress(identity["id"], course_id)
    percentage = get_course_progress_percentage(identity["id"], course_id)
    
    # Format and return progress JSON
    progress_data = to_json(progress)
    progress_data["progress_percentage"] = percentage
    return jsonify(progress_data)

@progress_bp.route("/api/courses/<course_id>/lessons/<lesson_id>/complete", methods=["POST"])
@jwt_required()
def mark_complete(course_id, lesson_id):
    """
    Marks a lesson as completed by the student.
    """
    identity = get_jwt_identity()
    if identity["role"] != "student":
        return jsonify({"error": "Unauthorized"}), 403
        
    progress = complete_lesson(identity["id"], course_id, lesson_id)
    percentage = get_course_progress_percentage(identity["id"], course_id)
    
    return jsonify({
        "message": "Lesson marked as completed",
        "progress_percentage": percentage,
        "progress": to_json(progress)
    })

@progress_bp.route("/api/courses/<course_id>/lessons/<lesson_id>/watch", methods=["POST"])
@jwt_required()
def mark_watched(course_id, lesson_id):
    """
    Marks a lesson video as watched by the student.
    """
    identity = get_jwt_identity()
    if identity["role"] != "student":
        return jsonify({"error": "Unauthorized"}), 403
        
    progress = watch_video(identity["id"], course_id, lesson_id)
    return jsonify({
        "message": "Video marked as watched",
        "progress": to_json(progress)
    })

@progress_bp.route("/api/courses/<course_id>/learning-time", methods=["POST"])
@jwt_required()
def log_learning_time(course_id):
    """
    Increments student learning time (in minutes) for a course.
    Expects JSON: {"minutes": N}
    """
    identity = get_jwt_identity()
    if identity["role"] != "student":
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json() or {}
    minutes = data.get("minutes", 1)
    
    progress = update_learning_time(identity["id"], course_id, minutes)
    return jsonify({
        "message": f"Added {minutes} minutes of learning time",
        "progress": to_json(progress)
    })
