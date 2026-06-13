from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models.quiz import (
    create_quiz, get_quiz_by_lesson, get_quiz_by_id, submit_quiz_score, get_student_score_for_quiz
)
from backend.models.course import get_lesson_by_id, get_course_by_id
from backend.services.gemini_service import generate_quiz_ai
from backend.utils.db import to_json

quizzes_bp = Blueprint("quizzes", __name__)

@quizzes_bp.route("/api/lessons/<lesson_id>/quiz", methods=["GET"])
@jwt_required()
def get_lesson_quiz(lesson_id):
    """
    Fetches the quiz for a lesson.
    Also checks if student has already completed it to show their score.
    """
    identity = get_jwt_identity()
    quiz = get_quiz_by_lesson(lesson_id)
    if not quiz:
        return jsonify({"quiz": None}), 200
        
    score_doc = None
    if identity["role"] == "student":
        score_doc = get_student_score_for_quiz(identity["id"], quiz["_id"])
        
    return jsonify({
        "quiz": to_json(quiz),
        "my_score": to_json(score_doc) if score_doc else None
    })

@quizzes_bp.route("/api/lessons/<lesson_id>/quiz/generate", methods=["POST"])
@jwt_required()
def generate_quiz(lesson_id):
    """
    Triggers Gemini AI to generate a quiz based on the lesson's metadata and notes content.
    Only teachers of the course can trigger this.
    """
    identity = get_jwt_identity()
    if identity["role"] != "teacher":
        return jsonify({"error": "Only teachers can generate quizzes"}), 403
        
    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        return jsonify({"error": "Lesson not found"}), 404
        
    course = get_course_by_id(lesson["course_id"])
    if not course or str(course["teacher_id"]) != identity["id"]:
        return jsonify({"error": "Unauthorized"}), 403
        
    # Generate quiz using Gemini API
    # Passes title, description, and placeholder notes text
    questions = generate_quiz_ai(lesson["title"], lesson["description"], lesson.get("notes_path", ""))
    
    if not questions:
        return jsonify({"error": "Failed to generate quiz questions via AI"}), 500
        
    quiz = create_quiz(course["_id"], lesson_id, questions)
    return jsonify({"message": "Quiz generated successfully", "quiz": to_json(quiz)}), 201

@quizzes_bp.route("/api/quizzes/<quiz_id>/submit", methods=["POST"])
@jwt_required()
def file_submit_quiz(quiz_id):
    """
    Submits student quiz answers, grades them, and saves the score in the database.
    Expects JSON: {"answers": ["A", "B", "C", "D", "A"]} (ordered list of selections)
    """
    identity = get_jwt_identity()
    if identity["role"] != "student":
        return jsonify({"error": "Only students can take quizzes"}), 403
        
    quiz = get_quiz_by_id(quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404
        
    data = request.get_json() or {}
    student_answers = data.get("answers", [])
    
    questions = quiz["questions"]
    total = len(questions)
    
    if len(student_answers) != total:
        return jsonify({"error": f"Invalid answers size. Expected {total} answers."}), 400
        
    # Grade answers
    correct_count = 0
    results = []
    
    for i, question in enumerate(questions):
        correct = question["correct_answer"].upper().strip()
        student_ans = str(student_answers[i]).upper().strip()
        
        is_correct = (student_ans == correct)
        if is_correct:
            correct_count += 1
            
        results.append({
            "question_index": i,
            "student_answer": student_ans,
            "correct_answer": correct,
            "is_correct": is_correct,
            "explanation": question.get("explanation", "")
        })
        
    score_doc = submit_quiz_score(identity["id"], quiz_id, correct_count, total)
    
    return jsonify({
        "message": "Quiz graded successfully",
        "score": correct_count,
        "total_questions": total,
        "results": results,
        "score_record": to_json(score_doc)
    })
