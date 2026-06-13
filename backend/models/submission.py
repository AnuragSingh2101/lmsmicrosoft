from datetime import datetime
from backend.utils.db import db, parse_id

submissions_col = db.submissions

def submit_assignment(assignment_id, student_id, file_path):
    """
    Submits an assignment. If submission already exists, overwrites it (resubmission).
    """
    aid = parse_id(assignment_id)
    sid = parse_id(student_id)
    
    if not aid or not sid:
        return None
    
    # Check if user already submitted
    existing = submissions_col.find_one({"assignment_id": aid, "student_id": sid})
    
    if existing:
        # Update existing submission (reset grade/feedback on resubmit)
        update_data = {
            "file_path": file_path,
            "submitted_at": datetime.utcnow(),
            "grade": None,
            "feedback": None
        }
        submissions_col.update_one({"_id": existing["_id"]}, {"$set": update_data})
        existing.update(update_data)
        return existing
    else:
        submission_doc = {
            "assignment_id": aid,
            "student_id": sid,
            "file_path": file_path,
            "submitted_at": datetime.utcnow(),
            "grade": None,
            "feedback": None
        }
        result = submissions_col.insert_one(submission_doc)
        submission_doc["_id"] = result.inserted_id
        return submission_doc

def get_submissions_by_assignment(assignment_id):
    """
    Fetches all submissions for an assignment, join with user details for teacher.
    """
    aid = parse_id(assignment_id)
    if not aid:
        return []
    
    pipeline = [
        {"$match": {"assignment_id": aid}},
        {
            "$lookup": {
                "from": "users",
                "localField": "student_id",
                "foreignField": "_id",
                "as": "student"
            }
        },
        {"$unwind": "$student"},
        {
            "$project": {
                "_id": 1,
                "assignment_id": 1,
                "student_id": 1,
                "file_path": 1,
                "submitted_at": 1,
                "grade": 1,
                "feedback": 1,
                "student_name": "$student.name",
                "student_email": "$student.email"
            }
        },
        {"$sort": {"submitted_at": -1}}
    ]
    return list(submissions_col.aggregate(pipeline))

def get_submissions_by_student(student_id):
    """
    Fetches all submissions made by a student.
    """
    sid = parse_id(student_id)
    if not sid:
        return []
    return list(submissions_col.find({"student_id": sid}))

def get_student_submission(assignment_id, student_id):
    """
    Fetches a student's submission for a specific assignment.
    """
    aid = parse_id(assignment_id)
    sid = parse_id(student_id)
    if not aid or not sid:
        return None
    return submissions_col.find_one({"assignment_id": aid, "student_id": sid})

def grade_submission(submission_id, grade, feedback):
    """
    Updates the grade and feedback for a submission.
    """
    oid = parse_id(submission_id)
    if not oid:
        return None
        
    update_data = {
        "grade": float(grade) if grade is not None else None,
        "feedback": feedback.strip() if feedback else ""
    }
    
    result = submissions_col.update_one({"_id": oid}, {"$set": update_data})
    if result.matched_count > 0:
        return submissions_col.find_one({"_id": oid})
    return None
