import asyncio
import uuid
import time
from typing import Any, Optional

from google.cloud.firestore_v1 import FieldFilter

from config import db, bucket

USERS = "users"
HOMEWORKS = "homeworks"
QUIZZES = "quizzes"
PAYMENTS = "payments"
LESSONS = "lessons"
COURSES = "courses"
COURSE_LESSONS = "course_lessons"

# ---------- Courses ----------

def _create_course_sync(data: dict) -> str:
    data.setdefault("created_at", time.time())
    ref = db.collection(COURSES).document()
    ref.set(data)
    return ref.id

async def create_course(data: dict) -> str:
    return await _run(_create_course_sync, data)

def _update_course_sync(course_id: str, data: dict) -> None:
    db.collection(COURSES).document(course_id).set(data, merge=True)

async def update_course(course_id: str, data: dict) -> None:
    await _run(_update_course_sync, course_id, data)

def _get_course_sync(course_id: str) -> Optional[dict]:
    doc = db.collection(COURSES).document(course_id).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    d["id"] = doc.id
    return d

async def get_course(course_id: str) -> Optional[dict]:
    return await _run(_get_course_sync, course_id)

def _list_courses_sync(category: str = None) -> list[dict]:
    query = db.collection(COURSES)
    if category:
        query = query.where(filter=FieldFilter("category", "==", category))
    result = []
    for doc in query.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        result.append(d)
    
    def get_sort_key(x):
        try:
            return int(x.get("course_number", 0))
        except ValueError:
            return 0
            
    result.sort(key=get_sort_key)
    return result

async def list_courses(category: str = None) -> list[dict]:
    return await _run(_list_courses_sync, category)

def _delete_course_sync(course_id: str) -> None:
    db.collection(COURSES).document(course_id).delete()

async def delete_course(course_id: str) -> None:
    await _run(_delete_course_sync, course_id)

# ---------- Course Lessons ----------

def _get_course_lesson_sync(course_id: str, lesson_num: int) -> Optional[dict]:
    query = db.collection(COURSE_LESSONS).where(filter=FieldFilter("course_id", "==", course_id)).where(filter=FieldFilter("lesson_number", "==", lesson_num)).limit(1)
    docs = list(query.stream())
    if not docs:
        return None
    d = docs[0].to_dict()
    d["id"] = docs[0].id
    return d

async def get_course_lesson(course_id: str, lesson_num: int) -> Optional[dict]:
    return await _run(_get_course_lesson_sync, course_id, lesson_num)

def _update_course_lesson_sync(course_id: str, lesson_num: int, data: dict) -> None:
    existing = _get_course_lesson_sync(course_id, lesson_num)
    if existing:
        db.collection(COURSE_LESSONS).document(existing["id"]).set(data, merge=True)
    else:
        data["course_id"] = course_id
        data["lesson_number"] = lesson_num
        data["created_at"] = time.time()
        db.collection(COURSE_LESSONS).document().set(data)

async def update_course_lesson(course_id: str, lesson_num: int, data: dict) -> None:
    await _run(_update_course_lesson_sync, course_id, lesson_num, data)

def _get_course_lessons_sync(course_id: str) -> list[dict]:
    query = db.collection(COURSE_LESSONS).where(filter=FieldFilter("course_id", "==", course_id))
    result = []
    for doc in query.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        result.append(d)
    result.sort(key=lambda x: int(x.get("lesson_number", 0)))
    return result

async def get_course_lessons(course_id: str) -> list[dict]:
    return await _run(_get_course_lessons_sync, course_id)

# ---------- Lessons (admin tomonidan qo'shilgan vazifalar) ----------

def _create_lesson_sync(data: dict) -> str:
    data.setdefault("created_at", time.time())
    data.setdefault("active", True)
    ref = db.collection(LESSONS).document()
    ref.set(data)
    return ref.id


async def create_lesson(data: dict) -> str:
    return await _run(_create_lesson_sync, data)


def _list_lessons_sync(category: str = None) -> list[dict]:
    result = []
    query = db.collection(LESSONS)
    if category:
        query = query.where(filter=FieldFilter("category", "==", category))
    for doc in query.stream():
        d = doc.to_dict()
        if d.get("active", True):
            d["id"] = doc.id
            result.append(d)
    result.sort(key=lambda x: x.get("created_at", 0))
    return result


async def list_lessons(category: str = None) -> list[dict]:
    return await _run(_list_lessons_sync, category)


def _delete_lesson_sync(lesson_id: str) -> None:
    db.collection(LESSONS).document(lesson_id).update({"active": False})


async def delete_lesson(lesson_id: str) -> None:
    await _run(_delete_lesson_sync, lesson_id)


def _get_lesson_sync(lesson_id: str) -> dict | None:
    doc = db.collection(LESSONS).document(lesson_id).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    d["id"] = doc.id
    return d


async def get_lesson(lesson_id: str) -> dict | None:
    return await _run(_get_lesson_sync, lesson_id)


async def _run(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


# ---------- Users ----------

def _get_user_sync(telegram_id: int) -> Optional[dict]:
    doc = db.collection(USERS).document(str(telegram_id)).get()
    return doc.to_dict() if doc.exists else None


async def get_user(telegram_id: int) -> Optional[dict]:
    return await _run(_get_user_sync, telegram_id)


def _create_user_sync(telegram_id: int, data: dict) -> None:
    data["telegram_id"] = telegram_id
    data.setdefault("role", "student")
    data.setdefault("created_at", time.time())
    data.setdefault("has_access", False)
    db.collection(USERS).document(str(telegram_id)).set(data)


async def create_user(telegram_id: int, data: dict) -> None:
    await _run(_create_user_sync, telegram_id, data)


def _update_user_sync(telegram_id: int, data: dict) -> None:
    db.collection(USERS).document(str(telegram_id)).update(data)


async def update_user(telegram_id: int, data: dict) -> None:
    await _run(_update_user_sync, telegram_id, data)


def _list_users_sync() -> list[dict]:
    return [d.to_dict() for d in db.collection(USERS).stream()]


async def list_users() -> list[dict]:
    return await _run(_list_users_sync)


async def is_admin(telegram_id: int) -> bool:
    user = await get_user(telegram_id)
    return bool(user and user.get("role") == "admin")


def _delete_user_sync(telegram_id: int) -> None:
    db.collection(USERS).document(str(telegram_id)).delete()

async def delete_user(telegram_id: int) -> None:
    await _run(_delete_user_sync, telegram_id)


# ---------- Storage ----------

def _upload_file_sync(local_path: str, dest_path: str) -> str:
    blob = bucket.blob(dest_path)
    blob.upload_from_filename(local_path)
    blob.make_public()
    return blob.public_url


async def upload_file(local_path: str, dest_path: str) -> str:
    return await _run(_upload_file_sync, local_path, dest_path)


def new_storage_path(user_id: int, kind: str, ext: str) -> str:
    return f"homeworks/{user_id}/{kind}_{uuid.uuid4().hex}.{ext}"


# ---------- Homeworks ----------

def _create_homework_sync(data: dict) -> str:
    data.setdefault("status", "pending")
    data.setdefault("submitted_at", time.time())
    data.setdefault("grade", None)
    data.setdefault("feedback", None)
    ref = db.collection(HOMEWORKS).document()
    ref.set(data)
    return ref.id


async def create_homework(data: dict) -> str:
    return await _run(_create_homework_sync, data)


def _get_homework_sync(hw_id: str) -> Optional[dict]:
    doc = db.collection(HOMEWORKS).document(hw_id).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    d["id"] = doc.id
    return d


async def get_homework(hw_id: str) -> Optional[dict]:
    return await _run(_get_homework_sync, hw_id)


def _list_pending_homeworks_sync(limit: int = 20) -> list[dict]:
    result = []
    for doc in db.collection(HOMEWORKS).stream():
        d = doc.to_dict()
        if d.get("status") == "pending":
            d["id"] = doc.id
            result.append(d)
        if len(result) >= limit:
            break
    result.sort(key=lambda x: x.get("submitted_at", 0))
    return result


async def list_pending_homeworks(limit: int = 20) -> list[dict]:
    return await _run(_list_pending_homeworks_sync, limit)


def _update_homework_sync(hw_id: str, data: dict) -> None:
    db.collection(HOMEWORKS).document(hw_id).update(data)


async def update_homework(hw_id: str, data: dict) -> None:
    await _run(_update_homework_sync, hw_id, data)


# ---------- Quizzes ----------

def _create_quiz_sync(data: dict) -> str:
    data.setdefault("created_at", time.time())
    ref = db.collection(QUIZZES).document()
    ref.set(data)
    return ref.id

async def create_quiz(data: dict) -> str:
    return await _run(_create_quiz_sync, data)

def _list_quizzes_sync() -> list[dict]:
    result = []
    for doc in db.collection(QUIZZES).stream():
        d = doc.to_dict()
        d["id"] = doc.id
        result.append(d)
    result.sort(key=lambda x: x.get("created_at", 0))
    return result

async def list_quizzes() -> list[dict]:
    return await _run(_list_quizzes_sync)

def _delete_quiz_sync(quiz_id: str) -> None:
    db.collection(QUIZZES).document(quiz_id).delete()

async def delete_quiz(quiz_id: str) -> None:
    await _run(_delete_quiz_sync, quiz_id)

def _list_quizzes_by_level_sync(level: str, category: str = None) -> list[dict]:
    query = db.collection(QUIZZES).where(filter=FieldFilter("level", "==", level))
    if category:
        query = query.where(filter=FieldFilter("category", "==", category))
    result = []
    for doc in query.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        result.append(d)
    return result


async def list_quizzes_by_level(level: str, category: str = None) -> list[dict]:
    return await _run(_list_quizzes_by_level_sync, level, category)


def _record_quiz_result_sync(telegram_id: int, level: str, score: int, total: int) -> None:
    ref = db.collection(USERS).document(str(telegram_id))
    ref.set({"quiz_stats": {level: {"score": score, "total": total, "at": time.time()}}}, merge=True)


async def record_quiz_result(telegram_id: int, level: str, score: int, total: int) -> None:
    await _run(_record_quiz_result_sync, telegram_id, level, score, total)


# ---------- Payments ----------

def _create_payment_sync(data: dict) -> str:
    data.setdefault("status", "pending")
    data.setdefault("created_at", time.time())
    ref = db.collection(PAYMENTS).document()
    ref.set(data)
    return ref.id


async def create_payment(data: dict) -> str:
    return await _run(_create_payment_sync, data)


def _get_payment_sync(payment_id: str) -> Optional[dict]:
    doc = db.collection(PAYMENTS).document(payment_id).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    d["id"] = doc.id
    return d


async def get_payment(payment_id: str) -> Optional[dict]:
    return await _run(_get_payment_sync, payment_id)


def _update_payment_sync(payment_id: str, data: dict) -> None:
    db.collection(PAYMENTS).document(payment_id).update(data)


async def update_payment(payment_id: str, data: dict) -> None:
    await _run(_update_payment_sync, payment_id, data)


# ---------- Scores & Leaderboard ----------

def _get_student_scores_sync(telegram_id: int) -> dict:
    """Bir talabaning barcha balllarini hisoblaydi."""
    uid = str(telegram_id)

    # Uy vazifalari ballari (graded homeworks)
    hw_score = 0
    hw_count = 0
    for doc in db.collection(HOMEWORKS).stream():
        d = doc.to_dict()
        if str(d.get("user_id")) == uid and d.get("status") == "graded":
            try:
                hw_score += int(d.get("grade", 0))
                hw_count += 1
            except (ValueError, TypeError):
                pass

    # Quiz ballari
    user_doc = db.collection(USERS).document(uid).get()
    quiz_score = 0
    quiz_count = 0
    if user_doc.exists:
        user_data = user_doc.to_dict()
        quiz_stats = user_data.get("quiz_stats", {})
        for level, stats in quiz_stats.items():
            quiz_score += stats.get("score", 0)
            quiz_count += stats.get("total", 0)

    return {
        "hw_score": hw_score,
        "hw_count": hw_count,
        "quiz_score": quiz_score,
        "quiz_questions": quiz_count,
        "total_score": hw_score + quiz_score,
    }


async def get_student_scores(telegram_id: int) -> dict:
    return await _run(_get_student_scores_sync, telegram_id)


def _get_leaderboard_sync() -> list[dict]:
    """Barcha talabalar reytingini hisoblaydi."""
    # Barcha uy vazifalari graded
    hw_by_user: dict[str, int] = {}
    hw_count_by_user: dict[str, int] = {}
    for doc in db.collection(HOMEWORKS).stream():
        d = doc.to_dict()
        if d.get("status") == "graded":
            uid = str(d.get("user_id", ""))
            if uid:
                try:
                    hw_by_user[uid] = hw_by_user.get(uid, 0) + int(d.get("grade", 0))
                    hw_count_by_user[uid] = hw_count_by_user.get(uid, 0) + 1
                except (ValueError, TypeError):
                    pass

    # Barcha foydalanuvchilar
    leaderboard = []
    for doc in db.collection(USERS).stream():
        d = doc.to_dict()
        uid = str(d.get("telegram_id", doc.id))
        role = d.get("role", "student")
        if role == "admin":
            continue

        name = d.get("full_name") or d.get("name") or d.get("first_name") or "Nomsiz"
        username = d.get("username", "")

        hw_score = hw_by_user.get(uid, 0)
        hw_count = hw_count_by_user.get(uid, 0)

        quiz_score = 0
        quiz_questions = 0
        quiz_stats = d.get("quiz_stats", {})
        for level, stats in quiz_stats.items():
            quiz_score += stats.get("score", 0)
            quiz_questions += stats.get("total", 0)

        total = hw_score + quiz_score
        leaderboard.append({
            "telegram_id": uid,
            "name": name,
            "username": username,
            "hw_score": hw_score,
            "hw_count": hw_count,
            "quiz_score": quiz_score,
            "quiz_questions": quiz_questions,
            "total_score": total,
        })

    leaderboard.sort(key=lambda x: x["total_score"], reverse=True)
    return leaderboard


async def get_leaderboard() -> list[dict]:
    return await _run(_get_leaderboard_sync)
