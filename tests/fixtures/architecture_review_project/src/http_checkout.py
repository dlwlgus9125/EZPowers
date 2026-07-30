"""HTTP compatibility entry point."""

from src.order_rules import normalize_customer_id, quoted_total, validate_items


def handle_checkout(payload: dict, repository, notifier) -> dict:
    customer_id = normalize_customer_id(payload["customer_id"])
    validate_items(payload["items"])
    total = quoted_total(payload["items"])
    order = repository.insert(customer_id, payload["items"], total)
    notifier.accepted(order["id"], customer_id)
    return order
