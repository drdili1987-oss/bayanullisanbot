import os
import json
import firebase_admin
from firebase_admin import credentials, firestore, storage
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = {int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}

CLICK_SERVICE_ID = os.environ.get("CLICK_SERVICE_ID", "")
CLICK_MERCHANT_ID = os.environ.get("CLICK_MERCHANT_ID", "")
CLICK_SECRET_KEY = os.environ.get("CLICK_SECRET_KEY", "")
CLICK_MERCHANT_USER_ID = os.environ.get("CLICK_MERCHANT_USER_ID", "")

PAYME_MERCHANT_ID = os.environ.get("PAYME_MERCHANT_ID", "")
PAYME_SECRET_KEY = os.environ.get("PAYME_SECRET_KEY", "")
PAYME_TEST_MODE = os.environ.get("PAYME_TEST_MODE", "true").lower() == "true"

COURSE_PRICE = int(os.environ.get("COURSE_PRICE", "150000"))
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "")
PORT = int(os.environ.get("PORT", "8080"))

BRANCHES = [
    {"name": "Chilonzor filiali", "lat": 41.2856, "lon": 69.2034},
    {"name": "Yunusobod filiali", "lat": 41.3517, "lon": 69.2887},
]


def _init_firebase():
    if firebase_admin._apps:
        return firebase_admin.get_app()

    cred_env = os.environ["FIREBASE_CREDENTIALS_JSON"]
    bucket = os.environ["FIREBASE_STORAGE_BUCKET"]

    if os.path.isfile(cred_env):
        cred = credentials.Certificate(cred_env)
    else:
        cred = credentials.Certificate(json.loads(cred_env))

    return firebase_admin.initialize_app(cred, {"storageBucket": bucket})


_init_firebase()

db = firestore.client()
bucket = storage.bucket()
