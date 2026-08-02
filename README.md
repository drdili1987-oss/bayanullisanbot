# Arabic Course Telegram Bot

Python 3.11 + aiogram 3.x + Firebase Firestore/Storage. Includes registration,
voice/text/PDF homework review, quiz engine, Click/Payme payments, branch
locator, and admin broadcaster.

## Project layout

```
main.py                 Entry point: runs bot polling + webhook server concurrently
config.py                Env vars, Firebase Admin init
webhook_server.py        Click/Payme merchant callback endpoints (aiohttp)
handlers/
  registration.py         Language -> name -> phone -> Firestore user
  homework.py             Lesson pick, media upload, admin grading/feedback
  quiz.py                 Level pick, MCQ flow, score tracking
  payment.py              Click/Payme invoice link generation
  branches.py             Branch list + distance by location
  admin.py                Admin panel, pending homework list, broadcaster
services/
  firebase_service.py     All Firestore/Storage CRUD (async wrappers)
  payment_service.py      Click/Payme link + signature generation/verification
  geo_service.py          Haversine distance
keyboards/                Reply & inline keyboard builders
states/                   FSM state groups
middlewares/auth.py        Loads Firestore user into every update
scripts/seed_quizzes.py    Seed sample quiz questions into Firestore
```

## Setup

1. Create a Firebase project, enable Firestore + Storage, download a service
   account JSON (Project Settings -> Service Accounts).
2. `cp .env.example .env` and fill in `BOT_TOKEN`, `ADMIN_IDS`,
   `FIREBASE_CREDENTIALS_JSON` (path to the JSON, or the JSON itself for
   platforms without file storage), `FIREBASE_STORAGE_BUCKET`, Click/Payme
   credentials, `WEBHOOK_BASE_URL`.
3. `pip install -r requirements.txt`
4. `python scripts/seed_quizzes.py` to add sample questions.
5. `python main.py`

## Firestore security

Firestore is accessed only through the Admin SDK (server-side), so client
security rules can stay locked down (`allow read, write: if false;`). Do not
expose the service account key or Firestore directly to end users.

## Deploying to Render.com

- Push this repo to GitHub.
- On Render: New -> Web Service -> connect repo -> "Docker" environment
  (uses the included `Dockerfile`), or import `render.yaml` as a Blueprint.
- Set all env vars from `.env.example` in the Render dashboard. For
  `FIREBASE_CREDENTIALS_JSON`, paste the full service account JSON as the
  value (the code accepts either a file path or a raw JSON string).
- Set `WEBHOOK_BASE_URL` to the Render service URL, and register
  `https://<service>.onrender.com/click/webhook` and
  `.../payme/webhook` in the Click/Payme merchant cabinets.
- The bot runs via long polling; the same process also serves the payment
  webhooks on `$PORT`, so Render's web service health check (`/health`)
  passes.

## Notes / production hardening still needed

- `blob.make_public()` in `firebase_service.upload_file` makes homework
  media publicly readable via URL. For private audio (tajweed submissions),
  switch to signed URLs (`blob.generate_signed_url`) if that's a requirement.
- Add Firestore composite indexes if `list_pending_homeworks` grows (single
  `where` + `order_by` on the same field needs no extra index, but adding
  more filters later will).
- Add rate limiting / anti-spam on the `/payme/webhook` and `/click/webhook`
  endpoints (currently open to any caller who passes signature/auth checks,
  which is the standard model for these providers, but consider IP allow-listing
  Click/Payme's published server IPs).
