import unittest

from src.batch_checkout import import_order
from src.http_checkout import handle_checkout


class Repository:
    def __init__(self) -> None:
        self.orders = []

    def insert(self, customer_id, items, total):
        order = {
            "id": len(self.orders) + 1,
            "customer_id": customer_id,
            "items": items,
            "total": total,
        }
        self.orders.append(order)
        return order


class Notifier:
    def __init__(self) -> None:
        self.notices = []

    def accepted(self, order_id, customer_id):
        self.notices.append((order_id, customer_id))


class CheckoutTests(unittest.TestCase):
    def scenario(self, entrypoint):
        repository = Repository()
        notifier = Notifier()
        order = entrypoint(
            {
                "customer_id": "  CUSTOMER-7 ",
                "items": [{"price": 25, "quantity": 2}],
            },
            repository,
            notifier,
        )
        self.assertEqual(order["customer_id"], "customer-7")
        self.assertEqual(order["total"], 50)
        self.assertEqual(notifier.notices, [(1, "customer-7")])

    def test_http_checkout(self):
        self.scenario(handle_checkout)

    def test_batch_checkout(self):
        self.scenario(import_order)


if __name__ == "__main__":
    unittest.main()
