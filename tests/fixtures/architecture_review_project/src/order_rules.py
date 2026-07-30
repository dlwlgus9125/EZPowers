"""Shared Order rules whose required call sequence still leaks to callers."""


def normalize_customer_id(raw_customer_id: str) -> str:
    return raw_customer_id.strip().lower()


def validate_items(items: list[dict[str, int]]) -> None:
    if not items:
        raise ValueError("an Order requires at least one item")
    if any(item["quantity"] <= 0 for item in items):
        raise ValueError("item quantity must be positive")


def quoted_total(items: list[dict[str, int]]) -> int:
    return sum(item["price"] * item["quantity"] for item in items)
