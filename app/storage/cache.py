from threading import Lock
from app.models.review import Review

_store: dict[str, list[Review]] = {}
_lock = Lock()


def save(app_id: str, reviews: list[Review]) -> None:
    with _lock:
        _store[app_id] = reviews


def get(app_id: str) -> list[Review] | None:
    with _lock:
        return _store.get(app_id)


def has(app_id: str) -> bool:
    with _lock:
        return app_id in _store


def clear() -> None:
    with _lock:
        _store.clear()
