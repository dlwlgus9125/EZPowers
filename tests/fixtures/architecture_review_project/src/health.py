"""Stable health behavior outside the named Order intake scope."""


def health_status() -> dict[str, str]:
    return {"status": "ok"}
