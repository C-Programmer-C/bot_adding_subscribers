import hashlib
import hmac
import re
from flask import request
from app.utils import log_and_abort
from conf.config import settings

def verify_signature(message: bytes, secret: str, signature: str) -> bool:
    """Проверка HMAC-SHA1 сигнатуры."""
    mac = hmac.new(secret.encode(), message, hashlib.sha1)
    return hmac.compare_digest(mac.hexdigest(), signature.lower())

def validate_pyrus_request(request, secret):
    """
    Проверяет User-Agent, X-Pyrus-Sig и X-Pyrus-Retry.
    Возвращает сырые байты тела запроса или вызывает log_and_abort.
    """
    raw = request.get_data(cache=True)

    ua = request.headers.get('User-Agent', '')
    m = re.fullmatch(r'Pyrus-Bot-(\d+)', ua)
    if not m:
        return log_and_abort("invalid user agent")
    if int(m.group(1)) != 4:
        return log_and_abort("unsupported Pyrus API version")

    sig = request.headers.get('X-Pyrus-Sig', '')
    if not sig:
        return log_and_abort("missing signature")
    sig = sig.partition('=')[2] if '=' in sig else sig
    if not verify_signature(raw, secret, sig):
        return log_and_abort("invalid signature")

    print(request.headers)
    
    retry = request.headers.get('X-Pyrus-Retry')
    if retry not in ('0/3', '1/3', '2/3', '3/3'):
        return log_and_abort("invalid retry header")

    return raw