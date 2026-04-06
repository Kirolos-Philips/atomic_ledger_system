from decimal import Decimal
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from .factories import AccountFactory


class TransactionTests(APITestCase):
    def setUp(self):
        self.account = AccountFactory(
            owner_name="Test User", balance=Decimal("1000.0000")
        )

    @patch("ledger.signals.process_transaction_event.delay")
    def test_credit_and_debit(self, mock_task):
        """Parameterized: positive amount → CREDIT, negative → DEBIT."""
        cases = [
            ("500.00", "CREDIT", Decimal("1500.0000")),
            ("-200.00", "DEBIT", Decimal("1300.0000")),
        ]
        for amount, expected_type, expected_balance in cases:
            with self.subTest(amount=amount):
                res = self.client.post(
                    "/api/transactions/",
                    {"account": self.account.id, "amount": amount},
                    format="json",
                )
                self.assertEqual(res.status_code, status.HTTP_201_CREATED)
                self.assertEqual(res.data["transaction_type"], expected_type)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, expected_balance)

    @patch("ledger.signals.process_transaction_event.delay")
    def test_rejections(self, mock_task):
        """Insufficient funds and inactive accounts are rejected."""
        res = self.client.post(
            "/api/transactions/",
            {"account": self.account.id, "amount": "-5000.00"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        self.account.is_active = False
        self.account.save()
        res = self.client.post(
            "/api/transactions/",
            {"account": self.account.id, "amount": "100.00"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("ledger.signals.process_transaction_event.delay")
    def test_immutability(self, mock_task):
        create = self.client.post(
            "/api/transactions/",
            {"account": self.account.id, "amount": "100.00"},
            format="json",
        )
        tid = create.data["id"]
        for method in [self.client.put, self.client.delete]:
            with self.subTest(method=method.__name__):
                res = method(f"/api/transactions/{tid}/", {}, format="json")
                self.assertEqual(res.status_code, 405)
