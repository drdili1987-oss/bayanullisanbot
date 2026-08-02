TEXTS = {
    "choose_language": {"uz": "Tilni tanlang:", "ru": "Выберите язык:"},
    "enter_name": {"uz": "Ismingizni kiriting:", "ru": "Введите ваше имя:"},
    "share_phone": {
        "uz": "Telefon raqamingizni ulashing:",
        "ru": "Поделитесь своим номером телефона:",
    },
    "registered": {
        "uz": "Ro'yxatdan muvaffaqiyatli o'tdingiz!",
        "ru": "Вы успешно зарегистрированы!",
    },
    "main_menu": {"uz": "Asosiy menyu", "ru": "Главное меню"},
    "choose_lesson": {"uz": "Darsni tanlang:", "ru": "Выберите урок:"},
    "send_homework": {
        "uz": "Ovozli xabar, matn, rasm yoki PDF yuboring:",
        "ru": "Отправьте голосовое сообщение, текст, фото или PDF:",
    },
    "homework_received": {
        "uz": "Uy vazifangiz qabul qilindi, tekshiruvda.",
        "ru": "Ваше домашнее задание принято, ожидает проверки.",
    },
    "choose_level": {"uz": "Darajani tanlang:", "ru": "Выберите уровень:"},
    "quiz_finished": {
        "uz": "Test yakunlandi. Natija: {score}/{total}",
        "ru": "Тест завершён. Результат: {score}/{total}",
    },
    "not_registered": {
        "uz": "Iltimos, avval /start orqali ro'yxatdan o'ting.",
        "ru": "Пожалуйста, сначала зарегистрируйтесь через /start.",
    },
    "no_access": {
        "uz": "Ushbu bo'limga kirish uchun kursga to'lov qiling.",
        "ru": "Для доступа к разделу оплатите курс.",
    },
    "pay_course": {
        "uz": "Kurs narxi: {price} so'm",
        "ru": "Стоимость курса: {price} сум",
    },
    "payment_success": {
        "uz": "To'lov muvaffaqiyatli amalga oshirildi! Kursga kirish ochildi.",
        "ru": "Оплата прошла успешно! Доступ к курсу открыт.",
    },
    "branches": {"uz": "Bizning filiallar:", "ru": "Наши филиалы:"},
}


def t(key: str, lang: str, **kwargs) -> str:
    lang = lang if lang in ("uz", "ru") else "uz"
    template = TEXTS.get(key, {}).get(lang, key)
    return template.format(**kwargs) if kwargs else template
