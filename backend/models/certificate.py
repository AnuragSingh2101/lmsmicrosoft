from datetime import datetime
from backend.utils.db import db, parse_id

certificates_col = db.certificates

def create_certificate(student_id, course_id, certificate_id, file_path):
    """
    Saves the certificate information to the database.
    """
    sid = parse_id(student_id)
    cid = parse_id(course_id)
    if not sid or not cid:
        return None
        
    # Check if certificate already exists
    existing = certificates_col.find_one({"student_id": sid, "course_id": cid})
    if existing:
        return existing
        
    certificate_doc = {
        "student_id": sid,
        "course_id": cid,
        "certificate_id": certificate_id,
        "issue_date": datetime.utcnow(),
        "file_path": file_path
    }
    
    result = certificates_col.insert_one(certificate_doc)
    certificate_doc["_id"] = result.inserted_id
    return certificate_doc

def get_certificate_by_id(certificate_id):
    """
    Fetches a certificate by its unique certificate ID string.
    """
    return certificates_col.find_one({"certificate_id": certificate_id})

def get_student_certificates(student_id):
    """
    Fetches all certificates earned by a student joined with course names.
    """
    sid = parse_id(student_id)
    if not sid:
        return []
        
    pipeline = [
        {"$match": {"student_id": sid}},
        {
            "$lookup": {
                "from": "courses",
                "localField": "course_id",
                "foreignField": "_id",
                "as": "course"
            }
        },
        {"$unwind": "$course"},
        {
            "$project": {
                "_id": 1,
                "certificate_id": 1,
                "course_id": 1,
                "issue_date": 1,
                "file_path": 1,
                "course_title": "$course.title"
            }
        }
    ]
    return list(certificates_col.aggregate(pipeline))

def get_course_certificate_for_student(student_id, course_id):
    """
    Checks if a student already has a certificate for a specific course.
    """
    sid = parse_id(student_id)
    cid = parse_id(course_id)
    if not sid or not cid:
        return None
    return certificates_col.find_one({"student_id": sid, "course_id": cid})
