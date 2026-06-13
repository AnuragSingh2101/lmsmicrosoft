from datetime import datetime
from backend.utils.db import db, parse_id

quizzes_col = db.quizzes
quiz_scores_col = db.quiz_scores

def create_quiz(course_id, lesson_id, questions):
    """
    Saves a generated quiz. If a quiz already exists for the lesson,
    it updates and replaces the questions with the new ones.
    """
    cid = parse_id(course_id)
    lid = parse_id(lesson_id)
    if not cid or not lid:
        return None
        
    existing = quizzes_col.find_one({"lesson_id": lid})
    if existing:
        quizzes_col.update_one(
            {"_id": existing["_id"]},
            {"$set": {"questions": questions, "created_at": datetime.utcnow()}}
        )
        existing["questions"] = questions
        return existing
    else:
        quiz_doc = {
            "course_id": cid,
            "lesson_id": lid,
            "questions": questions,  # list of question objects
            "created_at": datetime.utcnow()
        }
        result = quizzes_col.insert_one(quiz_doc)
        quiz_doc["_id"] = result.inserted_id
        return quiz_doc

def get_quiz_by_lesson(lesson_id):
    """
    Fetches the quiz details for a specific lesson.
    """
    lid = parse_id(lesson_id)
    if not lid:
        return None
    return quizzes_col.find_one({"lesson_id": lid})

def get_quiz_by_id(quiz_id):
    """
    Fetches quiz by its primary key ObjectId.
    """
    qid = parse_id(quiz_id)
    if not qid:
        return None
    return quizzes_col.find_one({"_id": qid})

def submit_quiz_score(student_id, quiz_id, score, total_questions):
    """
    Records a student's quiz attempt score. If score already exists, keeps the highest score.
    """
    sid = parse_id(student_id)
    qid = parse_id(quiz_id)
    if not sid or not qid:
        return None
        
    existing = quiz_scores_col.find_one({"student_id": sid, "quiz_id": qid})
    if existing:
        if score > existing["score"]:
            quiz_scores_col.update_one(
                {"_id": existing["_id"]},
                {"$set": {"score": float(score), "total_questions": int(total_questions), "submitted_at": datetime.utcnow()}}
            )
            existing.update({"score": float(score), "total_questions": int(total_questions), "submitted_at": datetime.utcnow()})
        return existing
    else:
        score_doc = {
            "student_id": sid,
            "quiz_id": qid,
            "score": float(score),
            "total_questions": int(total_questions),
            "submitted_at": datetime.utcnow()
        }
        result = quiz_scores_col.insert_one(score_doc)
        score_doc["_id"] = result.inserted_id
        return score_doc

def get_quiz_scores_by_student(student_id):
    """
    Fetches all quiz scores obtained by a student.
    """
    sid = parse_id(student_id)
    if not sid:
        return []
        
    pipeline = [
        {"$match": {"student_id": sid}},
        {
            "$lookup": {
                "from": "quizzes",
                "localField": "quiz_id",
                "foreignField": "_id",
                "as": "quiz"
            }
        },
        {"$unwind": "$quiz"},
        {
            "$lookup": {
                "from": "lessons",
                "localField": "quiz.lesson_id",
                "foreignField": "_id",
                "as": "lesson"
            }
        },
        {"$unwind": "$lesson"},
        {
            "$project": {
                "_id": 1,
                "quiz_id": 1,
                "score": 1,
                "total_questions": 1,
                "submitted_at": 1,
                "lesson_title": "$lesson.title",
                "course_id": "$quiz.course_id"
            }
        }
    ]
    return list(quiz_scores_col.aggregate(pipeline))

def get_student_score_for_quiz(student_id, quiz_id):
    """
    Helper to check if student has already completed a quiz and get their score.
    """
    sid = parse_id(student_id)
    qid = parse_id(quiz_id)
    if not sid or not qid:
        return None
    return quiz_scores_col.find_one({"student_id": sid, "quiz_id": qid})
