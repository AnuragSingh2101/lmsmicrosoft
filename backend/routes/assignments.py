import os
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models.assignment import (
    create_assignment, get_assignments_by_course, get_assignment_by_id, delete_assignment
)
from backend.models.submission import (
    submit_assignment, get_submissions_by_assignment, get_student_submission, grade_submission
)
from backend.models.course import get_course_by_id
from backend.utils.db import to_json, to_json_list
from backend.routes.courses import save_uploaded_file

assignments_bp = Blueprint("assignments", __name__)

ALLOWED_SUBMISSION_EXTENSIONS = {"pdf", "zip", "rar", "docx", "txt", "png", "jpg"}

@assignments_bp.route("/api/courses/<course_id>/assignments", methods=["GET"])
@jwt_required()
def list_assignments(course_id):
    assignments = get_assignments_by_course(course_id)
    return jsonify(to_json_list(assignments))

@assignments_bp.route("/api/courses/<course_id>/assignments", methods=["POST"])
@jwt_required()
def add_assignment(course_id):
    identity = get_jwt_identity()
    course = get_course_by_id(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
        
    if identity["role"] != "teacher" or str(course["teacher_id"]) != identity["id"]:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json() or {}
    title = data.get("title")
    instructions = data.get("instructions")
    due_date = data.get("due_date")
    max_marks = data.get("max_marks", 100)
    
    if not title or not instructions or not due_date:
        return jsonify({"error": "Missing title, instructions, or due_date"}), 400
        
    assignment = create_assignment(course_id, title, instructions, due_date, max_marks)
    return jsonify({"message": "Assignment created successfully", "assignment": to_json(assignment)}), 201

@assignments_bp.route("/api/assignments/<assignment_id>", methods=["GET"])
@jwt_required()
def get_assignment(assignment_id):
    assignment = get_assignment_by_id(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
    return jsonify(to_json(assignment))

@assignments_bp.route("/api/assignments/<assignment_id>", methods=["DELETE"])
@jwt_required()
def remove_assignment(assignment_id):
    identity = get_jwt_identity()
    assignment = get_assignment_by_id(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
        
    course = get_course_by_id(assignment["course_id"])
    if identity["role"] != "teacher" or str(course["teacher_id"]) != identity["id"]:
        return jsonify({"error": "Unauthorized"}), 403
        
    delete_assignment(assignment_id)
    return jsonify({"message": "Assignment deleted successfully"})

# --- Submission & Grading Routes ---

@assignments_bp.route("/api/assignments/<assignment_id>/submit", methods=["POST"])
@jwt_required()
def file_submit(assignment_id):
    identity = get_jwt_identity()
    if identity["role"] != "student":
        return jsonify({"error": "Only students can submit assignments"}), 403
        
    assignment = get_assignment_by_id(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
        
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
        
    saved_path = save_uploaded_file(file, "submissions", ALLOWED_SUBMISSION_EXTENSIONS)
    if not saved_path:
        return jsonify({"error": "Invalid file type. Allowed files: PDF, ZIP, RAR, DOCX, TXT, images"}), 400
        
    submission = submit_assignment(assignment_id, identity["id"], saved_path)
    
    # Mark student progress: also increment completed assignments/learning time if needed
    # But just saving is perfect
    return jsonify({"message": "Assignment submitted successfully", "submission": to_json(submission)}), 200

@assignments_bp.route("/api/assignments/<assignment_id>/submissions", methods=["GET"])
@jwt_required()
def view_submissions(assignment_id):
    identity = get_jwt_identity()
    assignment = get_assignment_by_id(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
        
    course = get_course_by_id(assignment["course_id"])
    if identity["role"] != "teacher" or str(course["teacher_id"]) != identity["id"]:
        return jsonify({"error": "Unauthorized"}), 403
        
    submissions = get_submissions_by_assignment(assignment_id)
    return jsonify(to_json_list(submissions))

@assignments_bp.route("/api/assignments/<assignment_id>/my-submission", methods=["GET"])
@jwt_required()
def my_submission(assignment_id):
    identity = get_jwt_identity()
    if identity["role"] != "student":
        return jsonify({"error": "Unauthorized"}), 403
        
    submission = get_student_submission(assignment_id, identity["id"])
    return jsonify(to_json(submission))

@assignments_bp.route("/api/submissions/<submission_id>/grade", methods=["POST"])
@jwt_required()
def set_grade(submission_id):
    identity = get_jwt_identity()
    if identity["role"] != "teacher":
        return jsonify({"error": "Only teachers can grade assignments"}), 403
        
    data = request.get_json() or {}
    grade = data.get("grade")
    feedback = data.get("feedback", "")
    
    if grade is None:
        return jsonify({"error": "Missing grade"}), 400
        
    submission = grade_submission(submission_id, grade, feedback)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404
        
    return jsonify({"message": "Grade updated successfully", "submission": to_json(submission)})
