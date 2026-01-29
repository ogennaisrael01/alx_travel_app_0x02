import environ 
from pathlib import Path
import os
import requests
from django.db import transaction
import logging

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))
logger = logging.getLogger(__name__)

CHAPA_SECRET = env("CHAPA_SECRET_KEY").strip()
CHAPA_INIT_URL = env("CHAPA_INIT_URL")
BASE_URL = env("BASE_URL")
CHAPA_VERIFY_URL = env("CHAPA_VERIFY_URL")


def get_headers():
    if CHAPA_SECRET is None:
        raise ValueError("Chapa secret key is not set")
    headers = {
        'Authorization': f'Bearer {CHAPA_SECRET}',
        'Content-Type': 'application/json'
        }
    return headers

def payment_init(email: str, amount: float, first_name: str,
            last_name: str, pmt_ref: str, phone_number: str) -> dict: 

    if not any([email, amount, first_name, last_name, pmt_ref]):
        raise ValueError("All payment fields are required")

    if CHAPA_INIT_URL is None:
        raise ValueError("Initialization url is empty")

    payment_payload = {
        "email": "ogennaisrael@gmail.com",
        "first_name": first_name, 
        "last_name": last_name,
        "phone": phone_number,
        "tx_ref": pmt_ref,
        "amount": amount,
        "currency": "ETB",
        "callback_url": BASE_URL + "/api/v1/chapa/callback",
        "return_url": BASE_URL + "/api/v1/chapa/return",
        "customoization": {
            "title": "Payments for travel app",
            "description": "payments"
        }

    }
    try:
        response = requests.post(url=CHAPA_INIT_URL, json=payment_payload, headers=get_headers())
    except Exception:
        logger.exception("payment request failed", exc_info=True)
        raise
    return response.json()

def payment_verify(tx_ref: str):
    verify_url = CHAPA_VERIFY_URL + f"/{tx_ref}/"
    payload = ""
    headers = get_headers()
    try:
        response = requests.get(verify_url, data=payload, headers=headers)
    except Exception:
        raise
    return response.json()



