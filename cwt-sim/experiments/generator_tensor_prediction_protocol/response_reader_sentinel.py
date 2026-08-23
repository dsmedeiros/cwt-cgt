"""The only response-facing symbol: an unconditional refusal sentinel."""

from __future__ import annotations


class ResponseAccessBlocked(RuntimeError):
    """Raised whenever any caller attempts to cross the response boundary."""


def blocked_response_reader(*_args: object, **_kwargs: object) -> None:
    raise ResponseAccessBlocked("response access is unavailable in the pre-response source protocol")


def sentinel_record() -> dict[str, object]:
    refused = False
    message = ""
    try:
        blocked_response_reader()
    except ResponseAccessBlocked as exc:
        refused = True
        message = str(exc)
    return {
        "authority": "unconditional_response_reader_refusal",
        "response_reader_exists": False,
        "response_unlock_command_exists": False,
        "sentinel_refused": refused,
        "sentinel_message": message,
        "response_accessed": False,
    }
