import functools
import logging
import time
import requests
from conf.config import settings
from typing import Tuple, Type


AUTH_URL = "https://accounts.pyrus.com/api/v4/auth"


logger = logging.getLogger(__name__)

class APIError(RuntimeError):
    """Ошибка при получении токена."""

def retry_on_exception(tries: int = 2,
                       delay: float = 30.0,
                       exceptions: Tuple[Type[BaseException], ...] = (Exception,),
                       ):
    """
    Декоратор: выполнить функцию tries раз, если она падает одним из exceptions.
    Между попытками ждать delay секунд.
    Если unlock_on_fail=True, то после всех неудачных попыток вызвать unlock_task(task_id).
    """
    if tries < 1:
        raise ValueError(f"Было получено {tries} попыток, когда их должно быть >= 1.")

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, tries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    logger.warning(f"Attempt {attempt}/{tries} failed for {func.__name__}", exc_info=True)
                    if attempt < tries:
                        time.sleep(delay)
            if last_exc:
                raise last_exc
        return wrapper
    return decorator


def build_comments_api_url(task_id):
    return f"https://api.pyrus.com/v4/tasks/{task_id}/comments"

def parse_json_response(resp: requests.Response, context: str = "") -> dict:
    try:
        return resp.json()
    except ValueError as e:
        snippet = resp.text[:300].replace("\n", " ")
        msg = f"Couldn't parse the JSON in the response {context or 'API'}: {resp.status_code} {snippet}"
        raise RuntimeError(msg) from e



@retry_on_exception(tries=3, delay=30,
                    exceptions=(RuntimeError, requests.RequestException))
def get_token(login: str, security_key: str, timeout: int = 30) -> str:
    payload = {"login": login, "security_key": security_key}

    try:
        resp = requests.post(AUTH_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise APIError(f"Couldn't get a token: {e}") from e

    data = parse_json_response(resp, context="auth")

    token = data.get("access_token")

    if not token:
        raise APIError(f"The response does not contain a token: {data}")
    return token


@retry_on_exception(tries=3, delay=30,
                    exceptions=(RuntimeError, requests.RequestException))
def add_staff_to_subscribers(task_id: int, token: str, staff_id: int, timeout: int = 30):
    headers = {"Authorization": f"Bearer {token}"}
    url = build_comments_api_url(task_id)

    body = {
        "subscribers_added": [
            {"id": staff_id}
        ]
    }
    try:
        resp = requests.post(url, headers=headers, timeout=timeout, json=body)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise APIError(f"Couldn't add staff #{staff_id} for the issue #{task_id}: {e}") from e

    data = parse_json_response(resp, context="comments")

    if "task" in data and data["task"]:
        logger.info(f"staff #{staff_id} successfully added to subscribers in task #{task_id}.")
        return True
    raise APIError(f"Couldn't add staff: invalid API response task_id: #{task_id} staff_id: #{staff_id}: {data}")