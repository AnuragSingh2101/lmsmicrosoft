from flask import Blueprint, render_template, redirect, url_for, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models.course import get_all_courses, get_course_by_id, get_lessons_by_course, get_lesson_by_id
from backend.models.progress import get_student_enrollments, get_or_create_progress, get_course_progress_percentage
from backend.models.assignment import get_assignments_by_course, get_assignment_by_id
from backend.models.submission import get_student_submission, get_submissions_by_assignment
from backend.models.quiz import get_quiz_by_lesson, get_student_score_for_quiz
from backend.models.certificate import get_course_certificate_for_student
from backend.utils.db import to_json

views_bp = Blueprint("views", __name__)

@views_bp.route("/")
@jwt_required(optional=True)
def index():
    """
    Landing page redirector. Directs logged-in users to their respective role dashboard,
    and guests to the login page.
    """
    identity = get_jwt_identity()
    if not identity:
        return redirect(url_for("views.login_page"))
        
    if identity["role"] == "teacher":
        return redirect(url_for("views.teacher_dashboard_page"))
    else:
        return redirect(url_for("views.student_dashboard_page"))

@views_bp.route("/login")
@jwt_required(optional=True)
def login_page():
    identity = get_jwt_identity()
    if identity:
        return redirect(url_for("views.index"))
    return render_template("login.html")

@views_bp.route("/register")
@jwt_required(optional=True)
def register_page():
    identity = get_jwt_identity()
    if identity:
        return redirect(url_for("views.index"))
    return render_template("register.html")

# --- Dashboards ---

@views_bp.route("/dashboard/student")
@jwt_required(optional=True)
def student_dashboard_page():
    identity = get_jwt_identity()
    if not identity or identity["role"] != "student":
        return redirect(url_for("views.login_page"))
        
    return render_template("student_dashboard.html", user=identity)

@views_bp.route("/dashboard/teacher")
@jwt_required(optional=True)
def teacher_dashboard_page():
    identity = get_jwt_identity()
    if not identity or identity["role"] != "teacher":
        return redirect(url_for("views.login_page"))
        
    return render_template("teacher_dashboard.html", user=identity)

# --- Course Pages ---

@views_bp.route("/courses")
@jwt_required(optional=True)
def browse_courses_page():
    identity = get_jwt_identity()
    if not identity:
        return redirect(url_for("views.login_page"))
        
    category = request.args.get("category", "")
    all_courses = get_all_courses(category if category else None)
    
    # Identify what courses student is already enrolled in
    enrolled_ids = []
    if identity["role"] == "student":
        enrollments = get_student_enrollments(identity["id"])
        enrolled_ids = [str(e["course_id"]) for e in enrollments]
        
    # Get distinct categories for course filter menu
    db = current_app.extensions["pymongo_db"] if "pymongo_db" in current_app.extensions else None
    if not db:
        from backend.utils.db import db
    categories = db.courses.distinct("category")
    
    return render_template(
        "browse_courses.html",
        user=identity,
        courses=all_courses,
        enrolled_ids=enrolled_ids,
        categories=categories,
        selected_category=category
    )

@views_bp.route("/course/<course_id>")
@jwt_required(optional=True)
def course_detail_page(course_id):
    identity = get_jwt_identity()
    if not identity:
        return redirect(url_for("views.login_page"))
        
    course = get_course_by_id(course_id)
    if not course:
        return "Course not found", 404
        
    lessons = get_lessons_by_course(course_id)
    assignments = get_assignments_by_course(course_id)
    
    is_enrolled = False
    progress = None
    certificate = None
    
    if identity["role"] == "student":
        # Check enrollment progress
        progress_doc = db.progress.find_one({"student_id": parse_id(identity["id"]), "course_id": parse_id(course_id)}) if "db" in globals() else None
        if not progress_doc:
            from backend.utils.db import db as local_db
            progress_doc = local_db.progress.find_one({"student_id": local_db.parse_id(identity["id"]), "course_id": local_db.parse_id(course_id)})
            
        if progress_doc:
            is_enrolled = True
            progress = to_json(progress_doc)
            progress["progress_percentage"] = get_course_progress_percentage(identity["id"], course_id)
            
            # Check certificate status
            certificate = get_course_certificate_for_student(identity["id"], course_id)
            
    # Allow teachers who own the course or students who are enrolled to view the contents
    is_owner = (identity["role"] == "teacher" and str(course["teacher_id"]) == identity["id"])
    
    return render_template(
        "course_detail.html",
        user=identity,
        course=course,
        lessons=lessons,
        assignments=assignments,
        is_enrolled=is_enrolled,
        is_owner=is_owner,
        progress=progress,
        certificate=certificate
    )

@views_bp.route("/course/create")
@jwt_required(optional=True)
def course_create_page():
    identity = get_jwt_identity()
    if not identity or identity["role"] != "teacher":
        return redirect(url_for("views.login_page"))
    return render_template("course_create.html", user=identity)

@views_bp.route("/course/<course_id>/edit")
@jwt_required(optional=True)
def course_edit_page(course_id):
    identity = get_jwt_identity()
    if not identity or identity["role"] != "teacher":
        return redirect(url_for("views.login_page"))
        
    course = get_course_by_id(course_id)
    if not course or str(course["teacher_id"]) != identity["id"]:
        return "Unauthorized", 403
        
    return render_template("course_edit.html", user=identity, course=course)

# --- Lesson & Quiz Views ---

@views_bp.route("/lesson/<lesson_id>")
@jwt_required(optional=True)
def lesson_view_page(lesson_id):
    identity = get_jwt_identity()
    if not identity:
        return redirect(url_for("views.login_page"))
        
    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        return "Lesson not found", 404
        
    course = get_course_by_id(lesson["course_id"])
    
    # Check eligibility: must be the teacher or enrolled student
    is_owner = (identity["role"] == "teacher" and str(course["teacher_id"]) == identity["id"])
    is_enrolled = False
    progress = None
    
    if identity["role"] == "student":
        # Force progress tracker enrollment if not exists (to permit tracking stats)
        progress = get_or_create_progress(identity["id"], course["_id"])
        is_enrolled = True
        
    if not is_owner and not is_enrolled:
        return "Unauthorized. Please enroll in the course first.", 403
        
    # Get all course lessons for sidebar index
    all_lessons = get_lessons_by_course(course["_id"])
    
    # Fetch quiz availability for this lesson
    quiz = get_quiz_by_lesson(lesson_id)
    student_score = None
    if quiz and identity["role"] == "student":
        student_score = get_student_score_for_quiz(identity["id"], quiz["_id"])
        
    return render_template(
        "lesson_view.html",
        user=identity,
        lesson=lesson,
        course=course,
        all_lessons=all_lessons,
        progress=progress,
        quiz=quiz,
        student_score=student_score
    )

@views_bp.route("/quiz/<quiz_id>/take")
@jwt_required(optional=True)
def quiz_attempt_page(quiz_id):
    identity = get_jwt_identity()
    if not identity or identity["role"] != "student":
        return redirect(url_for("views.login_page"))
        
    from backend.models.quiz import get_quiz_by_id
    quiz = get_quiz_by_id(quiz_id)
    if not quiz:
        return "Quiz not found", 404
        
    lesson = get_lesson_by_id(quiz["lesson_id"])
    course = get_course_by_id(quiz["course_id"])
    
    return render_template(
        "quiz_attempt.html",
        user=identity,
        quiz=quiz,
        lesson=lesson,
        course=course
    )

# --- Chat Assistant Workspace ---

@views_bp.route("/chat-assistant")
@jwt_required(optional=True)
def chat_assistant_page():
    identity = get_jwt_identity()
    if not identity or identity["role"] != "student":
        return redirect(url_for("views.login_page"))
        
    # Load list of enrolled courses to support contextual study selectors
    enrollments = get_student_enrollments(identity["id"])
    
    return render_template("chat_assistant.html", user=identity, enrollments=enrollments)

# --- Assignment Workspace ---

@views_bp.route("/assignments/<assignment_id>")
@jwt_required(optional=True)
def assignment_detail_page(assignment_id):
    identity = get_jwt_identity()
    if not identity:
        return redirect(url_for("views.login_page"))
        
    assignment = get_assignment_by_id(assignment_id)
    if not assignment:
        return "Assignment not found", 404
        
    course = get_course_by_id(assignment["course_id"])
    is_owner = (identity["role"] == "teacher" and str(course["teacher_id"]) == identity["id"])
    
    submission = None
    submissions_list = []
    
    if identity["role"] == "student":
        submission = get_student_submission(assignment_id, identity["id"])
    elif is_owner:
        # Load all submissions for teachers
        submissions_list = get_submissions_by_assignment(assignment_id)
        
    return render_template(
        "assignment_detail.html",
        user=identity,
        assignment=assignment,
        course=course,
        is_owner=is_owner,
        submission=submission,
        submissions=submissions_list
    )
