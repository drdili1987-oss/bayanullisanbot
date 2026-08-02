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


# ---------- Lessons (admin tomonidan qo'shilgan vazifalar) ----------

def _create_lesson_sync(data: dict) -> str:
    data.setdefault("created_at", time.time())
    data.setdefault("active", True)
    ref = db.collection(LESSONS).document()
    ref.set(data)
    return ref.id


async def create_lesson(data: dict) -> str:
    return await _run(_create_lesson_sync, data)


def _list_lessons_sync() -> list[dict]:
    result = []
    for doc in db.collection(LESSONS).stream():
        d = doc.to_dict()
        if d.get("active", True):
            d["id"] = doc.id
            result.append(d)
    result.sort(key=lambda x: x.get("created_at", 0))
    return result


async def list_lessons() -> list[dict]:
    return await _run(_list_lessons_sync)


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

def _list_quizzes_by_level_sync(level: str) -> list[dict]:
    query = db.collection(QUIZZES).where(filter=FieldFilter("level", "==", level))
    result = []
    for doc in query.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        result.append(d)
    return result


async def list_quizzes_by_level(level: str) -> list[dict]:
    return await _run(_list_quizzes_by_level_sync, level)


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
