from decimal import Decimal
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from .factories import AccountFactory, TokenFactory, UserFactory


class TransferTests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        token = TokenFactory(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.source = AccountFactory(
            user=self.user, name="CURRENT", balance=Decimal("1000.0000")
        )
        self.dest = AccountFactory(
            user=self.user, name="SAVINGS", balance=Decimal("0.0000")
        )

    def _transfer(self, **overrides):
        payload = {
            "source_account": str(self.source.id),
            "destination_account": str(self.dest.id),
            "amount": "250.00",
        }
        payload.update(overrides)
        return self.client.post("/api/transfers/", payload, format="json")

    @patch("ledger.signals.process_transfer_event.delay")
    @patch("ledger.signals.process_transaction_event.delay")
    def test_successful_transfer_and_immutability(self, *mocks):
        res = self._transfer(description="Savings deposit")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.source.refresh_from_db()
        self.dest.refresh_from_db()
        self.assertEqual(self.source.balance, Decimal("750.0000"))
        self.assertEqual(self.dest.balance, Decimal("250.0000"))

        # Immutability
        tid = res.data["id"]
        for method in [self.client.put, self.client.delete]:
            with self.subTest(method=method.__name__):
                self.assertEqual(
                    method(f"/api/transfers/{tid}/", {}, format="json").status_code, 405
                )

    def test_rejections(self):
        """Parameterized: various invalid transfer scenarios."""
        cases = [
            {"amount": "99999.00"},  # insufficient funds
            {"destination_account": str(self.source.id)},  # same account
            {"source_account": "00000000-0000-0000-0000-000000000000"},  # nonexistent
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides):
                res = self._transfer(**overrides)
                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
