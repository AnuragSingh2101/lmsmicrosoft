from datetime import datetime
from backend.utils.db import db, parse_id

chat_history_col = db.chat_history

def get_chat_history(student_id, course_id):
    """
    Fetches the chat history document for a student and optional course.
    Returns the message array list or an empty list if none exists.
    """
    sid = parse_id(student_id)
    cid = parse_id(course_id)
    if not sid:
        return []
        
    query = {"student_id": sid, "course_id": cid}
    chat = chat_history_col.find_one(query)
    if chat:
        return chat.get("messages", [])
    return []

def append_chat_message(student_id, course_id, sender, text):
    """
    Appends a new message to the chat history, creating the document if it doesn't exist.
    """
    sid = parse_id(student_id)
    cid = parse_id(course_id)
    if not sid:
        return None
        
    query = {"student_id": sid, "course_id": cid}
    message = {
        "sender": sender,  # 'user' or 'ai'
        "text": text.strip(),
        "timestamp": datetime.utcnow()
    }
    
    result = chat_history_col.update_one(
        query,
        {"$push": {"messages": message}},
        upsert=True
    )
    return message
