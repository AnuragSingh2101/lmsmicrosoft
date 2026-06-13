from datetime import datetime
from backend.utils.db import db, parse_id

courses_col = db.courses
lessons_col = db.lessons

def create_course(title, description, category, thumbnail, teacher_id):
    """
    Creates a new course.
    """
    course_doc = {
        "title": title.strip(),
        "description": description.strip(),
        "category": category.strip(),
        "thumbnail": thumbnail,
        "teacher_id": parse_id(teacher_id),
        "created_at": datetime.utcnow()
    }
    result = courses_col.insert_one(course_doc)
    course_doc["_id"] = result.inserted_id
    return course_doc

def update_course(course_id, title, description, category, thumbnail=None):
    """
    Updates course details. If thumbnail is None, keep original.
    """
    oid = parse_id(course_id)
    if not oid:
        return None
    
    update_data = {
        "title": title.strip(),
        "description": description.strip(),
        "category": category.strip()
    }
    if thumbnail:
        update_data["thumbnail"] = thumbnail
        
    result = courses_col.update_one({"_id": oid}, {"$set": update_data})
    if result.matched_count > 0:
        return courses_col.find_one({"_id": oid})
    return None

def delete_course(course_id):
    """
    Deletes a course and all associated lessons.
    """
    oid = parse_id(course_id)
    if not oid:
        return False
    
    # Delete all lessons belonging to the course
    lessons_col.delete_many({"course_id": oid})
    
    # Delete the course
    result = courses_col.delete_one({"_id": oid})
    return result.deleted_count > 0

def get_course_by_id(course_id):
    """
    Fetches a single course by ID.
    """
    oid = parse_id(course_id)
    if not oid:
        return None
    return courses_col.find_one({"_id": oid})

def get_all_courses(category=None):
    """
    Fetches all courses, optionally filtered by category.
    """
    query = {}
    if category:
        query["category"] = category
    return list(courses_col.find(query).sort("created_at", -1))

def get_courses_by_teacher(teacher_id):
    """
    Fetches all courses created by a specific teacher.
    """
    oid = parse_id(teacher_id)
    if not oid:
        return []
    return list(courses_col.find({"teacher_id": oid}).sort("created_at", -1))

# --- Lesson Functions ---

def create_lesson(course_id, title, description, youtube_id, notes_path, duration):
    """
    Creates a new lesson under a course.
    """
    lesson_doc = {
        "course_id": parse_id(course_id),
        "title": title.strip(),
        "description": description.strip(),
        "youtube_id": youtube_id.strip() if youtube_id else "",
        "notes_path": notes_path,  # Path to PDF note
        "duration": int(duration) if duration else 0,  # minutes
        "created_at": datetime.utcnow()
    }
    result = lessons_col.insert_one(lesson_doc)
    lesson_doc["_id"] = result.inserted_id
    return lesson_doc

def update_lesson(lesson_id, title, description, youtube_id, notes_path=None, duration=None):
    """
    Updates lesson details. Keep existing notes_path if new one not provided.
    """
    oid = parse_id(lesson_id)
    if not oid:
        return None
    
    update_data = {
        "title": title.strip(),
        "description": description.strip(),
        "youtube_id": youtube_id.strip() if youtube_id else ""
    }
    if notes_path is not None:
        update_data["notes_path"] = notes_path
    if duration is not None:
        update_data["duration"] = int(duration)
        
    result = lessons_col.update_one({"_id": oid}, {"$set": update_data})
    if result.matched_count > 0:
        return lessons_col.find_one({"_id": oid})
    return None

def delete_lesson(lesson_id):
    """
    Deletes a lesson.
    """
    oid = parse_id(lesson_id)
    if not oid:
        return False
    result = lessons_col.delete_one({"_id": oid})
    return result.deleted_count > 0

def get_lessons_by_course(course_id):
    """
    Fetches all lessons in a course.
    """
    oid = parse_id(course_id)
    if not oid:
        return []
    return list(lessons_col.find({"course_id": oid}).sort("created_at", 1))

def get_lesson_by_id(lesson_id):
    """
    Fetches a single lesson by ID.
    """
    oid = parse_id(lesson_id)
    if not oid:
        return None
    return lessons_col.find_one({"_id": oid})
