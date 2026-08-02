import base64
import hashlib
from urllib.parse import urlencode

from config import (
    CLICK_SERVICE_ID,
    CLICK_MERCHANT_ID,
    CLICK_SECRET_KEY,
    PAYME_MERCHANT_ID,
    PAYME_SECRET_KEY,
    WEBHOOK_BASE_URL,
)

CLICK_ERROR_SUCCESS = 0
CLICK_ERROR_SIGN_FAILED = -1
CLICK_ERROR_ALREADY_PAID = -4
CLICK_ERROR_TRANSACTION_NOT_FOUND = -6

PAYME_ERROR_INVALID_AMOUNT = -31001
PAYME_ERROR_TRANSACTION_NOT_FOUND = -31003
PAYME_ERROR_CANT_CANCEL = -31007
PAYME_ERROR_ALREADY_DONE = -31060


def generate_click_link(order_id: str, amount: int) -> str:
    params = {
        "service_id": CLICK_SERVICE_ID,
        "merchant_id": CLICK_MERCHANT_ID,
        "amount": amount,
        "transaction_param": order_id,
        "return_url": WEBHOOK_BASE_URL,
    }
    return f"https://my.click.uz/services/pay?{urlencode(params)}"


def click_signature(
    click_trans_id: str,
    service_id: str,
    merchant_trans_id: str,
    amount: str,
    action: str,
    sign_time: str,
    merchant_prepare_id: str = "",
) -> str:
    parts = [click_trans_id, service_id, CLICK_SECRET_KEY, merchant_trans_id]
    if merchant_prepare_id:
        parts.append(merchant_prepare_id)
    parts += [amount, action, sign_time]
    return hashlib.md5("".join(str(p) for p in parts).encode()).hexdigest()


def verify_click_signature(data: dict) -> bool:
    expected = click_signature(
        click_trans_id=data.get("click_trans_id", ""),
        service_id=data.get("service_id", ""),
        merchant_trans_id=data.get("merchant_trans_id", ""),
        amount=data.get("amount", ""),
        action=data.get("action", ""),
        sign_time=data.get("sign_time", ""),
        merchant_prepare_id=data.get("merchant_prepare_id", ""),
    )
    return expected == data.get("sign_string", "")


def generate_payme_link(order_id: str, amount: int) -> str:
    amount_tiyin = amount * 100
    raw = f"m={PAYME_MERCHANT_ID};ac.order_id={order_id};a={amount_tiyin}"
    encoded = base64.b64encode(raw.encode()).decode()
    return f"https://checkout.paycom.uz/{encoded}"


def verify_payme_auth(auth_header: str) -> bool:
    if not auth_header or not auth_header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(auth_header.split(" ", 1)[1]).decode()
        login, password = decoded.split(":", 1)
    except Exception:
        return False
    return login == "Paycom" and password == PAYME_SECRET_KEY
