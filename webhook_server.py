import time
import logging

from aiohttp import web
from aiogram import Bot

from config import COURSE_PRICE
from services import firebase_service as fb
from services.payment_service import (
    verify_click_signature,
    verify_payme_auth,
    CLICK_ERROR_SUCCESS,
    CLICK_ERROR_SIGN_FAILED,
    CLICK_ERROR_ALREADY_PAID,
    CLICK_ERROR_TRANSACTION_NOT_FOUND,
    PAYME_ERROR_INVALID_AMOUNT,
    PAYME_ERROR_TRANSACTION_NOT_FOUND,
    PAYME_ERROR_CANT_CANCEL,
)

log = logging.getLogger("webhook")


async def _grant_access(bot: Bot, payment_id: str) -> None:
    payment = await fb.get_payment(payment_id)
    if not payment:
        return
    await fb.update_payment(payment_id, {"status": "paid"})
    await fb.update_user(payment["user_id"], {"has_access": True})
    try:
        await bot.send_message(payment["user_id"], "✅ To'lov tasdiqlandi! Kursga kirish ochildi.")
    except Exception:
        log.exception("Failed to notify user about payment")


def create_webhook_app(bot: Bot) -> web.Application:
    app = web.Application()

    async def click_prepare(request: web.Request) -> web.Response:
        data = dict(await request.post())
        order_id = data.get("merchant_trans_id", "")

        if not verify_click_signature(data):
            return web.json_response({"error": CLICK_ERROR_SIGN_FAILED, "error_note": "Invalid signature"})

        payment = await fb.get_payment(order_id)
        if not payment:
            return web.json_response({"error": CLICK_ERROR_TRANSACTION_NOT_FOUND, "error_note": "Not found"})
        if payment.get("status") == "paid":
            return web.json_response({"error": CLICK_ERROR_ALREADY_PAID, "error_note": "Already paid"})

        return web.json_response(
            {
                "click_trans_id": data.get("click_trans_id"),
                "merchant_trans_id": order_id,
                "merchant_prepare_id": order_id,
                "error": CLICK_ERROR_SUCCESS,
                "error_note": "Success",
            }
        )

    async def click_complete(request: web.Request) -> web.Response:
        data = dict(await request.post())
        order_id = data.get("merchant_trans_id", "")

        if not verify_click_signature(data):
            return web.json_response({"error": CLICK_ERROR_SIGN_FAILED, "error_note": "Invalid signature"})

        error_code = int(data.get("error", "0"))
        if error_code == 0:
            await _grant_access(bot, order_id)

        return web.json_response(
            {
                "click_trans_id": data.get("click_trans_id"),
                "merchant_trans_id": order_id,
                "merchant_confirm_id": order_id,
                "error": CLICK_ERROR_SUCCESS,
                "error_note": "Success",
            }
        )

    async def click_webhook(request: web.Request) -> web.Response:
        data = dict(await request.post())
        action = data.get("action")
        if action == "0":
            return await click_prepare(request)
        return await click_complete(request)

    async def payme_webhook(request: web.Request) -> web.Response:
        auth_header = request.headers.get("Authorization", "")
        body = await request.json()
        req_id = body.get("id")

        if not verify_payme_auth(auth_header):
            return web.json_response(
                {"error": {"code": -32504, "message": "Insufficient privilege"}, "id": req_id}
            )

        method = body.get("method")
        params = body.get("params", {})

        if method == "CheckPerformTransaction":
            order_id = params.get("account", {}).get("order_id")
            amount = params.get("amount", 0)
            payment = await fb.get_payment(order_id)
            if not payment:
                return web.json_response({"error": {"code": PAYME_ERROR_TRANSACTION_NOT_FOUND}, "id": req_id})
            if amount != COURSE_PRICE * 100:
                return web.json_response({"error": {"code": PAYME_ERROR_INVALID_AMOUNT}, "id": req_id})
            return web.json_response({"result": {"allow": True}, "id": req_id})

        if method == "CreateTransaction":
            order_id = params.get("account", {}).get("order_id")
            trans_id = params.get("id")
            payment = await fb.get_payment(order_id)
            if not payment:
                return web.json_response({"error": {"code": PAYME_ERROR_TRANSACTION_NOT_FOUND}, "id": req_id})

            await fb.update_payment(
                order_id,
                {"payme_transaction_id": trans_id, "payme_state": 1, "payme_create_time": int(time.time() * 1000)},
            )
            return web.json_response(
                {
                    "result": {
                        "transaction": order_id,
                        "state": 1,
                        "create_time": int(time.time() * 1000),
                    },
                    "id": req_id,
                }
            )

        if method == "PerformTransaction":
            trans_id = params.get("id")
            payment_id = trans_id
            payment = await fb.get_payment(payment_id)
            if not payment:
                return web.json_response({"error": {"code": PAYME_ERROR_TRANSACTION_NOT_FOUND}, "id": req_id})

            await fb.update_payment(payment_id, {"payme_state": 2, "payme_perform_time": int(time.time() * 1000)})
            await _grant_access(bot, payment_id)
            return web.json_response(
                {"result": {"transaction": payment_id, "perform_time": int(time.time() * 1000), "state": 2}, "id": req_id}
            )

        if method == "CancelTransaction":
            trans_id = params.get("id")
            payment = await fb.get_payment(trans_id)
            if not payment:
                return web.json_response({"error": {"code": PAYME_ERROR_TRANSACTION_NOT_FOUND}, "id": req_id})

            if payment.get("payme_state") == 2:
                return web.json_response({"error": {"code": PAYME_ERROR_CANT_CANCEL}, "id": req_id})

            await fb.update_payment(trans_id, {"payme_state": -1, "status": "cancelled"})
            return web.json_response(
                {"result": {"transaction": trans_id, "cancel_time": int(time.time() * 1000), "state": -1}, "id": req_id}
            )

        if method == "CheckTransaction":
            trans_id = params.get("id")
            payment = await fb.get_payment(trans_id)
            if not payment:
                return web.json_response({"error": {"code": PAYME_ERROR_TRANSACTION_NOT_FOUND}, "id": req_id})
            return web.json_response(
                {
                    "result": {
                        "create_time": payment.get("payme_create_time", 0),
                        "perform_time": payment.get("payme_perform_time", 0),
                        "cancel_time": 0,
                        "transaction": trans_id,
                        "state": payment.get("payme_state", 1),
                    },
                    "id": req_id,
                }
            )

        return web.json_response({"error": {"code": -32601, "message": "Method not found"}, "id": req_id})

    async def health(request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    app.router.add_get("/health", health)
    app.router.add_post("/click/webhook", click_webhook)
    app.router.add_post("/payme/webhook", payme_webhook)
    return app
