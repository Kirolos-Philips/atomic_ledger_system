from decimal import Decimal
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from .factories import AccountFactory


class IdempotencyTests(APITestCase):
    def setUp(self):
        self.account = AccountFactory(
            owner_name="Test User", balance=Decimal("1000.0000")
        )

    @patch("ledger.signals.process_transaction_event.delay")
    def test_duplicate_key_rejected_unique_keys_succeed(self, mock_task):
        """Parameterized: duplicate keys fail, distinct keys succeed, null keys always pass."""
        cases = [
            ("key-a", "key-a", True),  # duplicate → second rejected
            ("key-x", "key-y", False),  # different → both succeed
            (None, None, False),  # null → both succeed
        ]
        for key1, key2, should_reject_second in cases:
            with self.subTest(key1=key1, key2=key2):
                acct = AccountFactory(
                    owner_name="Idem Use", balance=Decimal("1000.0000")
                )
                p1 = {"account": acct.id, "amount": "100.00", "idempotency_key": key1}
                p2 = {"account": acct.id, "amount": "100.00", "idempotency_key": key2}

                first = self.client.post("/api/transactions/", p1, format="json")
                second = self.client.post("/api/transactions/", p2, format="json")
                self.assertEqual(first.status_code, status.HTTP_201_CREATED)

                if should_reject_second:
                    self.assertIn(
                        second.status_code,
                        [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT],
                    )
                    acct.refresh_from_db()
                    self.assertEqual(acct.balance, Decimal("1100.0000"))
                else:
                    self.assertEqual(second.status_code, status.HTTP_201_CREATED)
                    acct.refresh_from_db()
                    self.assertEqual(acct.balance, Decimal("1200.0000"))
