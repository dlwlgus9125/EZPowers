"""Batch compatibility entry point."""

from src.order_rules import normalize_customer_id, quoted_total, validate_items


def import_order(row: dict, repository, notifier) -> dict:
    customer_id = normalize_customer_id(row["customer_id"])
    validate_items(row["items"])
    total = quoted_total(row["items"])
    order = repository.insert(customer_id, row["items"], total)
    notifier.accepted(order["id"], customer_id)
    return order
