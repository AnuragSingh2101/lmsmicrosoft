from datetime import datetime
from backend.utils.db import db, parse_id

assignments_col = db.assignments

def create_assignment(course_id, title, instructions, due_date, max_marks):
    """
    Creates a new assignment under a course.
    due_date should be a datetime object or ISO-format string.
    """
    if isinstance(due_date, str):
        try:
            # Try to parse string to datetime
            due_date = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
        except Exception:
            # Fallback if parsing fails
            due_date = datetime.utcnow()
            
    assignment_doc = {
        "course_id": parse_id(course_id),
        "title": title.strip(),
        "instructions": instructions.strip(),
        "due_date": due_date,
        "max_marks": int(max_marks) if max_marks else 100,
        "created_at": datetime.utcnow()
    }
    result = assignments_col.insert_one(assignment_doc)
    assignment_doc["_id"] = result.inserted_id
    return assignment_doc

def get_assignments_by_course(course_id):
    """
    Fetch all assignments for a course.
    """
    oid = parse_id(course_id)
    if not oid:
        return []
    return list(assignments_col.find({"course_id": oid}).sort("created_at", -1))

def get_assignment_by_id(assignment_id):
    """
    Fetch a single assignment by ID.
    """
    oid = parse_id(assignment_id)
    if not oid:
        return None
    return assignments_col.find_one({"_id": oid})

def delete_assignment(assignment_id):
    """
    Delete an assignment.
    """
    oid = parse_id(assignment_id)
    if not oid:
        return False
    
    # Clean up associated submissions
    db.submissions.delete_many({"assignment_id": oid})
    
    result = assignments_col.delete_one({"_id": oid})
    return result.deleted_count > 0
