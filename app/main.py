from app.pyrus_api import APIError, add_staff_to_subscribers, get_token
from conf.logging_config import conf_logger
import logging
from flask import Flask, request
from waitress import serve  
from conf.config import settings
from app.utils import clean_phone_number, extract_telephone_number, get_json_path, get_staff_id_by_phone, log_and_abort, staff_is_subscriber
from app.verify_signature import validate_pyrus_request  

app = Flask(__name__)

logger = logging.getLogger(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    raw = validate_pyrus_request(request, settings.SECURITY_KEY)

    if not raw:
        return log_and_abort("invalid request")

    if not data:
        return log_and_abort("invalid or missing json")

    task = data.get("task")
    if not task:
        return log_and_abort("task not found")

    task_id = data.get("task_id") or (task or {}).get("id")

    if not task_id:
        return log_and_abort("task_id not found")

    logger.info(f"get new task #{task_id}")
    
    subscribers = task.get("subscribers", [])
    
    if not subscribers:
        return log_and_abort("subscribers not found")
    
    fields = task.get("fields")
    if not fields:
        return log_and_abort("fields not found in task #{task_id}")
    
    telephone_number = extract_telephone_number(fields)
    
    if not telephone_number:
        logger.warning(f"telephone number not found in task #{task_id}")
        return "", 200
    
    clear_number = clean_phone_number(telephone_number)
    
    if not clear_number:
        return "", 200
    
    json_path = get_json_path()
    
    staff_id = get_staff_id_by_phone(telephone_number, json_path)
    
    if not staff_id:
        logger.warning(f"staff_id not found for {telephone_number} in task #{task_id}")
        return "", 200
    
    try:
        if staff_id is not None:
            staff_id = int(staff_id)
        else:
            logger.warning(f"staff_id is None in task #{task_id}")
            return "", 200
    except (ValueError, TypeError) as e:
        logger.warning(f"Cannot convert staff_id '{staff_id}' to int in task #{task_id}: {e}")
        staff_id = None
        return "", 200
    
    in_task = staff_is_subscriber(staff_id, subscribers, task_id)
    
    if in_task:
        logger.info(f"staff exists in subscribers for task {task_id}")
        return "", 200

    try:
        token = get_token(settings.LOGIN, settings.SECURITY_KEY)
    except APIError:
        logger.exception("Error when receiving the token")
        raise
    
    try:
        add_staff_to_subscribers(task_id, token, staff_id)
    except APIError:
        logger.exception("Error when adding staff to subscribers")
        raise
    
    return "", 200


if __name__ == "__main__":
    conf_logger()
    logger.debug("Bot started.")
    try:
        serve(app, host="0.0.0.0", port=settings.PORT)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot has been stopped.")
