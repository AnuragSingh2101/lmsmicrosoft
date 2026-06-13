from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models.certificate import (
    create_certificate, get_certificate_by_id, get_course_certificate_for_student
)
from backend.models.course import get_course_by_id, get_lessons_by_course
from backend.models.user import get_user_by_id
from backend.models.progress import get_or_create_progress, get_course_progress_percentage
from backend.services.certificate_service import generate_certificate_pdf
from backend.utils.db import to_json

certificates_bp = Blueprint("certificates", __name__)

@certificates_bp.route("/api/courses/<course_id>/certificate", methods=["GET"])
@jwt_required()
def check_or_issue_certificate(course_id):
    """
    Checks if a student already has a certificate for the course.
    If not, checks eligibility (100% completion of course lessons)
    and automatically issues the certificate if eligible.
    """
    identity = get_jwt_identity()
    if identity["role"] != "student":
        return jsonify({"error": "Only students can receive certificates"}), 403
        
    student_id = identity["id"]
    
    # 1. Check if certificate is already issued
    cert = get_course_certificate_for_student(student_id, course_id)
    if cert:
        return jsonify({"issued": True, "certificate": to_json(cert)})
        
    # 2. Verify eligibility (progress must be 100%)
    progress = get_or_create_progress(student_id, course_id)
    lessons = get_lessons_by_course(course_id)
    
    if not lessons:
        return jsonify({"issued": False, "error": "This course has no lessons yet."}), 400
        
    completed_count = len(progress.get("completed_lessons", []))
    total_lessons = len(lessons)
    
    is_eligible = (completed_count >= total_lessons) and (total_lessons > 0)
    
    if not is_eligible:
        return jsonify({
            "issued": False,
            "reason": "Course is not fully completed",
            "completed_lessons": completed_count,
            "total_lessons": total_lessons,
            "progress_percentage": round((completed_count / total_lessons) * 100, 1)
        })
        
    # 3. Issue certificate
    user = get_user_by_id(student_id)
    course = get_course_by_id(course_id)
    
    if not user or not course:
        return jsonify({"error": "Failed to resolve student or course profile"}), 500
        
    # Trigger ReportLab generator
    cert_id, relative_path = generate_certificate_pdf(
        student_name=user["name"],
        course_name=course["title"]
    )
    
    cert_doc = create_certificate(student_id, course_id, cert_id, relative_path)
    
    return jsonify({
        "issued": True,
        "message": "Congratulations! Your certificate of completion has been issued.",
        "certificate": to_json(cert_doc)
    })

@certificates_bp.route("/verify/certificate/<certificate_id>", methods=["GET"])
def verify_certificate_web(certificate_id):
    """
    Public web page that verifies a certificate ID.
    Renders an HTML template.
    """
    cert = get_certificate_by_id(certificate_id)
    if not cert:
        return render_template("verify_certificate.html", cert=None, cert_id=certificate_id), 404
        
    student = get_user_by_id(cert["student_id"])
    course = get_course_by_id(cert["course_id"])
    
    student_name = student["name"] if student else "Unknown Student"
    course_title = course["title"] if course else "Unknown Course"
    
    formatted_date = cert["issue_date"]
    if isinstance(formatted_date, datetime):
        formatted_date = formatted_date.strftime("%B %d, %Y")
    elif isinstance(formatted_date, str):
        try:
            formatted_date = datetime.fromisoformat(formatted_date.replace("Z", "+00:00")).strftime("%B %d, %Y")
        except Exception:
            pass
            
    cert_details = {
        "certificate_id": cert["certificate_id"],
        "student_name": student_name,
        "course_title": course_title,
        "issue_date": formatted_date,
        "file_path": cert["file_path"]
    }
    
    return render_template("verify_certificate.html", cert=cert_details)
