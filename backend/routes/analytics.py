from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models.course import get_courses_by_teacher, get_lessons_by_course, get_all_courses
from backend.models.progress import get_student_enrollments, get_course_progress_percentage
from backend.models.quiz import get_quiz_scores_by_student
from backend.models.submission import get_submissions_by_assignment
from backend.models.assignment import get_assignments_by_course
from backend.services.gemini_service import get_smart_recommendations
from backend.utils.db import db, parse_id, to_json_list

analytics_bp = Blueprint("analytics", __name__)

@analytics_bp.route("/api/analytics/student", methods=["GET"])
@jwt_required()
def student_analytics():
    """
    Computes performance and progress statistics for the logged-in student,
    including AI course recommendations.
    """
    identity = get_jwt_identity()
    if identity["role"] != "student":
        return jsonify({"error": "Unauthorized"}), 403
        
    student_id = identity["id"]
    
    # 1. Fetch enrollments
    enrollments = get_student_enrollments(student_id)
    enrolled_count = len(enrollments)
    
    # Calculate completed courses (progress == 100%)
    completed_courses = [e for e in enrollments if e.get("progress_percentage", 0.0) >= 100.0]
    completed_count = len(completed_courses)
    
    # 2. Total learning time
    total_learning_time = sum(e.get("learning_time", 0) for e in enrollments)
    
    # 3. Quiz average score
    quiz_scores = get_quiz_scores_by_student(student_id)
    avg_score_pct = 0.0
    if quiz_scores:
        total_pct = sum((q["score"] / q["total_questions"]) * 100 for q in quiz_scores if q["total_questions"] > 0)
        avg_score_pct = round(total_pct / len(quiz_scores), 1)
        
    # 4. Assignment submission stats
    submissions = list(db.submissions.find({"student_id": parse_id(student_id)}))
    submitted_assignments_count = len(submissions)
    
    # Graded ratio
    graded_count = sum(1 for s in submissions if s.get("grade") is not None)
    
    # 5. Smart Recommendations (AI Powered)
    interests = request.args.get("interests", "Programming, Computer Science, Engineering")
    all_courses = get_all_courses()
    
    recommended = get_smart_recommendations(
        enrolled_courses=enrollments,
        completed_courses=completed_courses,
        quiz_scores=quiz_scores,
        interests=interests,
        all_courses=all_courses
    )
    
    # Format recommendations for frontend response
    formatted_recs = []
    for item in recommended:
        course_doc = item["course"]
        formatted_recs.append({
            "id": str(course_doc["_id"]),
            "title": course_doc["title"],
            "description": course_doc["description"],
            "category": course_doc["category"],
            "thumbnail": course_doc["thumbnail"],
            "reason": item["reason"]
        })
        
    return jsonify({
        "enrolled_count": enrolled_count,
        "completed_count": completed_count,
        "learning_time_minutes": total_learning_time,
        "quiz_average_percentage": avg_score_pct,
        "submitted_assignments_count": submitted_assignments_count,
        "graded_assignments_count": graded_count,
        "recommendations": formatted_recs
    })

@analytics_bp.route("/api/analytics/teacher", methods=["GET"])
@jwt_required()
def teacher_analytics():
    """
    Computes tracking metrics across all courses created by the logged-in teacher.
    """
    identity = get_jwt_identity()
    if identity["role"] != "teacher":
        return jsonify({"error": "Unauthorized"}), 403
        
    teacher_id = identity["id"]
    
    # Get all courses created by the teacher
    courses = get_courses_by_teacher(teacher_id)
    total_courses = len(courses)
    
    total_students_enrolled = 0
    total_completed = 0
    unique_student_ids = set()
    course_breakdown = []
    
    total_assignments_created = 0
    total_submissions_received = 0
    total_submissions_graded = 0
    
    for c in courses:
        c_id = c["_id"]
        # Find enrollments for this course
        enrollments = list(db.progress.find({"course_id": c_id}))
        enroll_count = len(enrollments)
        total_students_enrolled += enroll_count
        
        # Add student IDs to unique set
        for e in enrollments:
            unique_student_ids.add(str(e["student_id"]))
            
        # Count course completions
        lessons = get_lessons_by_course(c_id)
        total_lessons = len(lessons)
        comp_count = 0
        if total_lessons > 0:
            for e in enrollments:
                if len(e.get("completed_lessons", [])) >= total_lessons:
                    comp_count += 1
        total_completed += comp_count
        
        # Assignment metrics for this course
        course_assignments = get_assignments_by_course(c_id)
        total_assignments_created += len(course_assignments)
        
        for a in course_assignments:
            submissions = list(db.submissions.find({"assignment_id": a["_id"]}))
            total_submissions_received += len(submissions)
            total_submissions_graded += sum(1 for s in submissions if s.get("grade") is not None)
            
        course_breakdown.append({
            "id": str(c_id),
            "title": c["title"],
            "category": c["category"],
            "enrollment_count": enroll_count,
            "completion_count": comp_count,
            "lessons_count": total_lessons
        })
        
    return jsonify({
        "total_courses": total_courses,
        "total_enrollments": total_students_enrolled,
        "total_unique_students": len(unique_student_ids),
        "total_completions": total_completed,
        "total_assignments_created": total_assignments_created,
        "total_submissions_received": total_submissions_received,
        "total_submissions_graded": total_submissions_graded,
        "course_breakdown": course_breakdown
    })
