from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models.chat import get_chat_history, append_chat_message
from backend.models.course import get_lesson_by_id
from backend.services.gemini_service import chat_study_assistant
from backend.utils.db import to_json

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/api/chat/history", methods=["GET"])
@jwt_required()
def fetch_history():
    """
    Fetches dialogue history for the student and optional course.
    """
    identity = get_jwt_identity()
    if identity["role"] != "student":
        return jsonify({"error": "Only students can use the AI assistant"}), 403
        
    course_id = request.args.get("course_id")
    history = get_chat_history(identity["id"], course_id)
    return jsonify(to_json(history))

@chat_bp.route("/api/chat", methods=["POST"])
@jwt_required()
def send_message():
    """
    Receives user message, runs the AI assistant with history and lesson context,
    saves the conversation, and returns the response.
    Expects JSON: {"message": "Hello...", "course_id": "...", "lesson_id": "..."}
    """
    identity = get_jwt_identity()
    if identity["role"] != "student":
        return jsonify({"error": "Only students can use the AI assistant"}), 403
        
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    course_id = data.get("course_id")
    lesson_id = data.get("lesson_id")
    
    if not user_message:
        return jsonify({"error": "Message content is empty"}), 400
        
    # Get current history to pass as context
    history = get_chat_history(identity["id"], course_id)
    
    # Optional lesson context
    lesson_title = None
    lesson_desc = None
    if lesson_id:
        lesson = get_lesson_by_id(lesson_id)
        if lesson:
            lesson_title = lesson.get("title")
            lesson_desc = lesson.get("description")
            
    # Append student message to DB
    append_chat_message(identity["id"], course_id, "user", user_message)
    
    # Query AI generator
    ai_reply = chat_study_assistant(user_message, history, lesson_title, lesson_desc)
    
    # Append AI reply to DB
    append_chat_message(identity["id"], course_id, "ai", ai_reply)
    
    return jsonify({
        "reply": ai_reply,
        "sender": "ai"
    })
