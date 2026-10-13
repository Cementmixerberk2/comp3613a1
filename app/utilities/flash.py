import json

from fastapi import Request

_FLASH_COOKIE = "_flash_messages"


def _read_cookie_messages(request: Request):
    raw = request.cookies.get(_FLASH_COOKIE)
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return payload if isinstance(payload, list) else []


def flash(request: Request, message: str, type: str = "success") -> None:
    messages = _read_cookie_messages(request)
    messages.append({"message": message, "type": type})
    request.state._flash_messages = messages


def get_flashed_messages(request: Request):
    messages = _read_cookie_messages(request)
    if messages:
        request.state._flash_messages_to_clear = True
    return messages
