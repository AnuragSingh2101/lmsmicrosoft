from datetime import datetime
from backend.utils.db import db, parse_id
from backend.models.course import get_lessons_by_course

progress_col = db.progress

def get_or_create_progress(student_id, course_id):
    """
    Fetches progress record. If not enrolled/created, creates it (enrolls student).
    """
    sid = parse_id(student_id)
    cid = parse_id(course_id)
    if not sid or not cid:
        return None
        
    progress = progress_col.find_one({"student_id": sid, "course_id": cid})
    if not progress:
        progress_doc = {
            "student_id": sid,
            "course_id": cid,
            "completed_lessons": [],
            "watched_videos": [],
            "learning_time": 0,  # in minutes
            "last_active": datetime.utcnow()
        }
        result = progress_col.insert_one(progress_doc)
        progress_doc["_id"] = result.inserted_id
        return progress_doc
    return progress

def enroll_student_in_course(student_id, course_id):
    """
    Enrolls a student by generating their initial progress entry.
    """
    return get_or_create_progress(student_id, course_id)

def complete_lesson(student_id, course_id, lesson_id):
    """
    Add lesson to the list of completed lessons for a course.
    """
    sid = parse_id(student_id)
    cid = parse_id(course_id)
    lid = parse_id(lesson_id)
    
    if not sid or not cid or not lid:
        return None
        
    progress = get_or_create_progress(sid, cid)
    if not progress:
        return None
        
    if lid not in progress.get("completed_lessons", []):
        progress_col.update_one(
            {"_id": progress["_id"]},
            {
                "$addToSet": {"completed_lessons": lid},
                "$set": {"last_active": datetime.utcnow()}
            }
        )
        # Fetch updated doc
        progress = progress_col.find_one({"_id": progress["_id"]})
        
    return progress

def watch_video(student_id, course_id, lesson_id):
    """
    Add lesson to the list of watched video lessons.
    """
    sid = parse_id(student_id)
    cid = parse_id(course_id)
    lid = parse_id(lesson_id)
    
    if not sid or not cid or not lid:
        return None
        
    progress = get_or_create_progress(sid, cid)
    if not progress:
        return None
        
    if lid not in progress.get("watched_videos", []):
        progress_col.update_one(
            {"_id": progress["_id"]},
            {
                "$addToSet": {"watched_videos": lid},
                "$set": {"last_active": datetime.utcnow()}
            }
        )
        progress = progress_col.find_one({"_id": progress["_id"]})
        
    return progress

def update_learning_time(student_id, course_id, minutes):
    """
    Increments the accumulated learning time in minutes.
    """
    sid = parse_id(student_id)
    cid = parse_id(course_id)
    if not sid or not cid:
        return None
        
    progress = get_or_create_progress(sid, cid)
    if not progress:
        return None
        
    progress_col.update_one(
        {"_id": progress["_id"]},
        {
            "$inc": {"learning_time": int(minutes)},
            "$set": {"last_active": datetime.utcnow()}
        }
    )
    return progress_col.find_one({"_id": progress["_id"]})

def get_course_progress_percentage(student_id, course_id):
    """
    Calculates progress percentage: (completed lessons / total lessons) * 100.
    """
    sid = parse_id(student_id)
    cid = parse_id(course_id)
    if not sid or not cid:
        return 0.0
        
    total_lessons = len(get_lessons_by_course(cid))
    if total_lessons == 0:
        return 0.0
        
    progress = progress_col.find_one({"student_id": sid, "course_id": cid})
    if not progress:
        return 0.0
        
    completed_count = len(progress.get("completed_lessons", []))
    percentage = (completed_count / total_lessons) * 100.0
    return round(percentage, 1)

def get_student_enrollments(student_id):
    """
    Fetches all courses enrolled by a student joined with course metadata.
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
            "$lookup": {
                "from": "users",
                "localField": "course.teacher_id",
                "foreignField": "_id",
                "as": "teacher"
            }
        },
        {"$unwind": "$teacher"},
        {
            "$project": {
                "_id": 1,
                "course_id": 1,
                "completed_lessons": 1,
                "watched_videos": 1,
                "learning_time": 1,
                "last_active": 1,
                "course_title": "$course.title",
                "course_description": "$course.description",
                "course_category": "$course.category",
                "course_thumbnail": "$course.thumbnail",
                "teacher_name": "$teacher.name"
            }
        }
    ]
    
    enrollments = list(progress_col.aggregate(pipeline))
    for e in enrollments:
        e["progress_percentage"] = get_course_progress_percentage(student_id, e["course_id"])
    return enrollments
