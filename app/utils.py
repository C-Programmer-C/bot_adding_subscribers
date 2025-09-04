import json
import logging
import os
from pathlib import Path
import re
from typing import Iterable, Mapping, Any
from conf.config import settings
from flask import jsonify

logger = logging.getLogger(__name__)

def staff_is_subscriber(user_id: int, subscribers, task_id) -> bool:
    for subscriber in subscribers:
        person_id = subscriber.get("person", {}).get("id")
        if person_id == user_id:
            logger.info(f"Staff #{user_id} already is a subscriber for task {task_id}")
            return True

    logger.info("Staff #{user_id} is NOT a subscriber for task %s", user_id)
    return False

def clean_phone_number(value: str) -> str:
    """
    Оставляет только цифры в номере телефона.
    """
    if not value:
        return ""
    return re.sub(r"\D", "", value)

def get_json_path() -> str:
    return str(Path(__file__).resolve().parent.parent / "stuff_ids.json")

def get_staff_id_by_phone(phone: str, json_path) -> int | None:
    """Возвращает client_id по номеру телефона из JSON."""
    clear_number = clean_phone_number(phone)

    if not clear_number:
        return None
    
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"{json_path} not found")

    with open(json_path, "r", encoding="utf-8") as f:
        client_ids = json.load(f)

    return client_ids.get(clear_number)

def extract_telephone_number(fields: Iterable[Mapping[str, Any]], telephone_field_id: int = settings.TELEPHONE_FIELD_ID):
    for field in fields:
        if not isinstance(field, Mapping):
            continue

        if field.get("id") != telephone_field_id:
            continue
        
        value = field.get("value") or None
        
        return value

    return None
                    
def log_and_abort(message, task_id=None, code=400):
    logger.warning(f"task {task_id} {message}.")
    return jsonify({"error": message}), code
