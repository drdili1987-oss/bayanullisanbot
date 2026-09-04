import os
import time
import json
import logging
import hmac
import hashlib
from urllib.parse import parse_qsl

from aiohttp import web
from aiogram import Bot

from config import (
    BOT_TOKEN,
    ADMIN_IDS,
    COURSE_PRICE,
    WEBHOOK_BASE_URL,
    CLICK_SERVICE_ID,
    PAYME_MERCHANT_ID,
)
from services import firebase_service as fb
from services.payment_service import generate_click_link, generate_payme_link

log = logging.getLogger("webapp")


def verify_telegram_init_data(init_data: str) -> dict | None:
    """Verifies Telegram WebApp initData hash using BOT_TOKEN."""
    if not init_data:
        return None
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None

        # Build data-check-string
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if hmac.compare_digest(calculated_hash, received_hash):
            user_data = parsed.get("user")
            if user_data:
                return json.loads(user_data)
        return None
    except Exception as e:
        log.warning(f"Telegram initData verification error: {e}")
        return None


def register_webapp_routes(app: web.Application, bot: Bot, frontend_dir: str):
    """Registers all REST API endpoints and static file serving for WebApp."""

    # 1. Auth Endpoint
    async def api_auth(request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except Exception:
            body = {}

        init_data = body.get("initData", "")
        tg_user = verify_telegram_init_data(init_data)
        
        # Fallback for dev / direct browser testing
        user_id = None
        if tg_user:
            user_id = tg_user.get("id")
            first_name = tg_user.get("first_name", "")
            username = tg_user.get("username", "")
        else:
            user_id = body.get("userId")
            first_name = body.get("name", "Talaba")
            username = body.get("username", "")

        if not user_id:
            return web.json_response({"success": False, "error": "Foydalanuvchi aniqlanmadi"}, status=400)

        user_id = int(user_id) if str(user_id).isdigit() else user_id
        db_user = await fb.get_user(user_id)

        if not db_user:
            user_data = {
                "user_id": user_id,
                "first_name": first_name,
                "username": username,
                "language": "uz",
                "role": "admin" if user_id in ADMIN_IDS else "student",
                "allowed_courses": [],
                "has_access": False,
                "score": 0,
                "created_at": time.time(),
            }
            await fb.create_or_update_user(user_id, user_data)
            db_user = user_data
        else:
            if user_id in ADMIN_IDS and db_user.get("role") != "admin":
                db_user["role"] = "admin"
                await fb.update_user(user_id, {"role": "admin"})

        is_admin = user_id in ADMIN_IDS or db_user.get("role") == "admin"
        return web.json_response({
            "success": True,
            "user": {
                "id": user_id,
                "name": db_user.get("first_name", first_name),
                "username": db_user.get("username", username),
                "phone": db_user.get("phone", ""),
                "role": "admin" if is_admin else "student",
                "isAdmin": is_admin,
                "hasAccess": db_user.get("has_access", False),
                "allowedCourses": db_user.get("allowed_courses", []),
                "score": db_user.get("score", 0),
            }
        })

    # 2. Categories
    async def api_categories(request: web.Request) -> web.Response:
        categories = [
            {"id": "sarf", "title": "Sarf bo'limi", "icon": "📖", "desc": "So'z yasalishi va morfemika asoslari"},
            {"id": "nahv", "title": "Nahv bo'limi", "icon": "📜", "desc": "Gap tuzilishi va grammatika qoidalari"},
            {"id": "maoniy", "title": "Balog'at: Maoniy", "icon": "✨", "desc": "Ma'no va nutq mutanosibligi"},
            {"id": "bayon", "title": "Balog'at: Bayon", "icon": "💎", "desc": "Tashbeh, majoz va kinoya ilmi"},
            {"id": "badiy", "title": "Balog'at: Badiy", "icon": "🎨", "desc": "Lafziy va ma'naviy go'zalliklar"},
            {"id": "barmoq", "title": "She'riyat: Barmoq vazni", "icon": "🎵", "desc": "Hijo va barmoq ritmi"},
            {"id": "aruz", "title": "She'riyat: Aruz", "icon": "🎼", "desc": "Klassik aruz bahr va ruknlari"},
            {"id": "badiy_sanatlar", "title": "She'riyat: Badiy san'atlar", "icon": "🎭", "desc": "Nazmda so'z san'atlari"},
        ]
        return web.json_response({"success": True, "categories": categories})

    # 3. List Courses
    async def api_courses(request: web.Request) -> web.Response:
        category = request.query.get("category")
        user_id_param = request.query.get("userId")
        
        user_allowed = []
        is_admin = False
        if user_id_param:
            try:
                uid = int(user_id_param) if user_id_param.isdigit() else user_id_param
                u = await fb.get_user(uid)
                if u:
                    user_allowed = u.get("allowed_courses", [])
                    is_admin = uid in ADMIN_IDS or u.get("role") == "admin"
            except Exception:
                pass

        courses = await fb.list_courses(category if category else None)
        
        # Format response
        result = []
        for c in courses:
            c_id = c.get("id")
            has_access = is_admin or (c_id in user_allowed) or c.get("is_free", False)
            result.append({
                "id": c_id,
                "title": c.get("title", "Nomsiz kurs"),
                "category": c.get("category", ""),
                "courseNumber": c.get("course_number", 1),
                "description": c.get("description", ""),
                "price": c.get("price", COURSE_PRICE),
                "thumbnail": c.get("thumbnail", ""),
                "isPublished": c.get("is_published", True),
                "totalLessons": c.get("total_lessons", 0),
                "hasAccess": has_access,
            })
        return web.json_response({"success": True, "courses": result})

    # 4. Course Details & Lessons
    async def api_course_detail(request: web.Request) -> web.Response:
        course_id = request.match_info.get("id")
        user_id_param = request.query.get("userId")

        course = await fb.get_course(course_id)
        if not course:
            return web.json_response({"success": False, "error": "Kurs topilmadi"}, status=404)

        user_allowed = []
        is_admin = False
        if user_id_param:
            try:
                uid = int(user_id_param) if user_id_param.isdigit() else user_id_param
                u = await fb.get_user(uid)
                if u:
                    user_allowed = u.get("allowed_courses", [])
                    is_admin = uid in ADMIN_IDS or u.get("role") == "admin"
            except Exception:
                pass

        has_access = is_admin or (course_id in user_allowed) or course.get("is_free", False)
        lessons = await fb.get_course_lessons(course_id)

        formatted_lessons = []
        for l in lessons:
            is_preview = l.get("is_preview", False)
            can_view = has_access or is_preview
            formatted_lessons.append({
                "id": l.get("id"),
                "courseId": course_id,
                "lessonNumber": l.get("lesson_number", 1),
                "title": l.get("title", f"{l.get('lesson_number', 1)}-dars"),
                "description": l.get("description", ""),
                "videoUrl": l.get("video_url", "") if can_view else None,
                "audioUrl": l.get("audio_url", "") if can_view else None,
                "pdfUrl": l.get("pdf_url", "") if can_view else None,
                "phrase": l.get("phrase", l.get("arabic_text", "مَرْحَبًا")),
                "type": l.get("type", "video"),
                "isLocked": not can_view,
            })

        return web.json_response({
            "success": True,
            "course": {
                "id": course_id,
                "title": course.get("title", ""),
                "category": course.get("category", ""),
                "description": course.get("description", ""),
                "price": course.get("price", COURSE_PRICE),
                "thumbnail": course.get("thumbnail", ""),
                "hasAccess": has_access,
                "lessons": formatted_lessons,
            }
        })

    # 5. Single Lesson Detail (with full practice info)
    async def api_lesson_detail(request: web.Request) -> web.Response:
        course_id = request.match_info.get("course_id")
        lesson_num_str = request.match_info.get("lesson_num")
        user_id_param = request.query.get("userId")

        try:
            lesson_num = float(lesson_num_str)
        except ValueError:
            return web.json_response({"success": False, "error": "Noto'g'ri dars raqami"}, status=400)

        course = await fb.get_course(course_id)
        if not course:
            return web.json_response({"success": False, "error": "Kurs topilmadi"}, status=404)

        user_allowed = []
        is_admin = False
        if user_id_param:
            try:
                uid = int(user_id_param) if user_id_param.isdigit() else user_id_param
                u = await fb.get_user(uid)
                if u:
                    user_allowed = u.get("allowed_courses", [])
                    is_admin = uid in ADMIN_IDS or u.get("role") == "admin"
            except Exception:
                pass

        has_access = is_admin or (course_id in user_allowed) or course.get("is_free", False)
        lesson = await fb.get_course_lesson(course_id, lesson_num)

        if not lesson:
            return web.json_response({"success": False, "error": "Dars topilmadi"}, status=404)

        is_preview = lesson.get("is_preview", False)
        if not has_access and not is_preview:
            return web.json_response({"success": False, "error": "Ushbu dars uchun to'lov qilinishi kerak", "locked": True}, status=403)

        return web.json_response({
            "success": True,
            "lesson": {
                "id": lesson.get("id"),
                "courseId": course_id,
                "courseTitle": course.get("title", ""),
                "lessonNumber": lesson.get("lesson_number", lesson_num),
                "title": lesson.get("title", f"{lesson_num}-dars"),
                "description": lesson.get("description", ""),
                "videoUrl": lesson.get("video_url", ""),
                "audioUrl": lesson.get("audio_url", ""),
                "pdfUrl": lesson.get("pdf_url", ""),
                "phrase": lesson.get("phrase", lesson.get("arabic_text", "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ")),
                "translation": lesson.get("translation", "Mehribon va rahmli Alloh nomi bilan"),
                "notes": lesson.get("notes", ""),
                "type": lesson.get("type", "video"),
            }
        })

    # 6. Quizzes Endpoint
    async def api_quizzes(request: web.Request) -> web.Response:
        category = request.query.get("category")
        level = request.query.get("level")
        quizzes = await fb.list_quizzes(category if category else None, level if level else None)
        return web.json_response({"success": True, "quizzes": quizzes})

    # 7. Payment Generation (Click & Payme)
    async def api_create_payment(request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"success": False, "error": "Invalid body"}, status=400)

        user_id = body.get("userId")
        course_id = body.get("courseId")
        provider = body.get("provider", "click").lower()

        if not user_id or not course_id:
            return web.json_response({"success": False, "error": "userId va courseId zarur"}, status=400)

        course = await fb.get_course(course_id)
        amount = course.get("price", COURSE_PRICE) if course else COURSE_PRICE

        # Create payment record
        order_id = f"ORDER_{user_id}_{int(time.time())}"
        payment_doc = {
            "order_id": order_id,
            "user_id": user_id,
            "course_id": course_id,
            "amount": amount,
            "provider": provider,
            "status": "pending",
            "created_at": time.time(),
        }
        await fb.create_payment(payment_doc)

        if provider == "payme":
            pay_url = generate_payme_link(order_id, amount)
        else:
            pay_url = generate_click_link(order_id, amount)

        return web.json_response({
            "success": True,
            "orderId": order_id,
            "amount": amount,
            "paymentUrl": pay_url,
            "provider": provider,
        })

    # 8. Homework Submit
    async def api_submit_homework(request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"success": False, "error": "Invalid body"}, status=400)

        user_id = body.get("userId")
        course_id = body.get("courseId")
        lesson_num = body.get("lessonNumber", 1)
        text = body.get("text", "")
        audio_url = body.get("audioUrl", "")

        if not user_id:
            return web.json_response({"success": False, "error": "userId zarur"}, status=400)

        homework_data = {
            "user_id": user_id,
            "course_id": course_id,
            "lesson_number": lesson_num,
            "text": text,
            "audio_url": audio_url,
            "status": "pending",
            "created_at": time.time(),
        }
        hw_id = await fb.submit_homework(homework_data)

        # Notify admins in Telegram
        user = await fb.get_user(user_id)
        u_name = user.get("first_name", "O'quvchi") if user else "O'quvchi"
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"📥 <b>Yangi uyga vazifa topshirildi!</b>\n\n"
                    f"👤 O'quvchi: <b>{u_name}</b> (ID: <code>{user_id}</code>)\n"
                    f"📚 Kurs: <code>{course_id}</code>, {lesson_num}-dars\n"
                    f"📝 Matn: {text[:200] if text else 'Yo\'q'}\n"
                    f"🔗 Audio: {audio_url if audio_url else 'Yo\'q'}"
                )
            except Exception:
                pass

        return web.json_response({"success": True, "homeworkId": hw_id})

    # 9. Admin Stats & Course Management
    async def api_admin_save_course(request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"success": False, "error": "Invalid body"}, status=400)

        user_id = body.get("userId")
        if not user_id or int(user_id) not in ADMIN_IDS:
            return web.json_response({"success": False, "error": "Ruxsat yo'q"}, status=403)

        course_id = body.get("courseId")
        course_data = {
            "title": body.get("title", ""),
            "category": body.get("category", "sarf"),
            "course_number": int(body.get("courseNumber", 1)),
            "description": body.get("description", ""),
            "price": int(body.get("price", COURSE_PRICE)),
            "thumbnail": body.get("thumbnail", ""),
            "is_published": bool(body.get("isPublished", True)),
        }

        if course_id:
            await fb.update_course(course_id, course_data)
        else:
            course_id = await fb.create_course(course_data)

        return web.json_response({"success": True, "courseId": course_id})

    # 10. Admin Save Lesson
    async def api_admin_save_lesson(request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"success": False, "error": "Invalid body"}, status=400)

        user_id = body.get("userId")
        if not user_id or int(user_id) not in ADMIN_IDS:
            return web.json_response({"success": False, "error": "Ruxsat yo'q"}, status=403)

        course_id = body.get("courseId")
        lesson_num = float(body.get("lessonNumber", 1.0))
        lesson_data = {
            "title": body.get("title", ""),
            "description": body.get("description", ""),
            "video_url": body.get("videoUrl", ""),
            "audio_url": body.get("audioUrl", ""),
            "phrase": body.get("phrase", ""),
            "translation": body.get("translation", ""),
            "type": body.get("type", "video"),
            "is_preview": bool(body.get("isPreview", False)),
        }
        await fb.update_course_lesson(course_id, lesson_num, lesson_data)
        return web.json_response({"success": True})

    # Register API routes
    app.router.add_post("/api/webapp/auth", api_auth)
    app.router.add_get("/api/webapp/categories", api_categories)
    app.router.add_get("/api/webapp/courses", api_courses)
    app.router.add_get("/api/webapp/courses/{id}", api_course_detail)
    app.router.add_get("/api/webapp/lessons/{course_id}/{lesson_num}", api_lesson_detail)
    app.router.add_get("/api/webapp/quizzes", api_quizzes)
    app.router.add_post("/api/webapp/payments/create", api_create_payment)
    app.router.add_post("/api/webapp/homework/submit", api_submit_homework)
    app.router.add_post("/api/webapp/admin/save_course", api_admin_save_course)
    app.router.add_post("/api/webapp/admin/save_lesson", api_admin_save_lesson)

    # Static frontend files
    if os.path.exists(frontend_dir):
        async def index_handler(request: web.Request) -> web.FileResponse:
            index_path = os.path.join(frontend_dir, "index.html")
            return web.FileResponse(index_path)

        app.router.add_get("/", index_handler)
        app.router.add_get("/app", index_handler)
        static_dir = os.path.join(frontend_dir, "static")
        if os.path.exists(static_dir):
            app.router.add_static("/static/", static_dir, name="static")
