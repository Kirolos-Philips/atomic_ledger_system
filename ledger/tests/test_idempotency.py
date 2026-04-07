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
    def test_idempotency_first_request_success(self, mock_task):
        """Standard valid request with a unique key succeeds."""
        acct = AccountFactory(owner_name="Idem Use", balance=Decimal("1000.0000"))
        payload = {
            "account": acct.id,
            "amount": "100.00",
            "idempotency_key": "unique-k",
        }
        res = self.client.post("/api/transactions/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        acct.refresh_from_db()
        self.assertEqual(acct.balance, Decimal("1100.0000"))

    @patch("ledger.signals.process_transaction_event.delay")
    def test_idempotency_same_payload_replay_success(self, mock_task):
        """Replaying the exact same request payload returns the original result (201)."""
        acct = AccountFactory(owner_name="Idem Use", balance=Decimal("1000.0000"))
        payload = {
            "account": acct.id,
            "amount": "100.00",
            "idempotency_key": "replay-k",
        }

        # First call
        res1 = self.client.post("/api/transactions/", payload, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Second call (Replay)
        res2 = self.client.post("/api/transactions/", payload, format="json")
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res2.data["id"], res1.data["id"])

        acct.refresh_from_db()
        self.assertEqual(
            acct.balance, Decimal("1100.0000")
        )  # Balance only affected once

    @patch("ledger.signals.process_transaction_event.delay")
    def test_idempotency_mismatch_payload_conflict(self, mock_task):
        """Using the same key for a different payload (mismatched amount) results in 409."""
        acct = AccountFactory(owner_name="Idem Use", balance=Decimal("1000.0000"))
        key = "shared-k"

        # First call: $100
        self.client.post(
            "/api/transactions/",
            {"account": acct.id, "amount": "100.00", "idempotency_key": key},
            format="json",
        )

        # Second call: $200 (Conflict)
        res = self.client.post(
            "/api/transactions/",
            {"account": acct.id, "amount": "200.00", "idempotency_key": key},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

        acct.refresh_from_db()
        self.assertEqual(
            acct.balance, Decimal("1100.0000")
        )  # Only first request applied

    def test_idempotency_distinct_keys(self):
        """Distinct keys for the same user always succeed."""
        acct = AccountFactory(owner_name="Idem Use", balance=Decimal("1000.0000"))
        self.client.post(
            "/api/transactions/",
            {"account": acct.id, "amount": "100.00", "idempotency_key": "k1"},
            format="json",
        )
        res = self.client.post(
            "/api/transactions/",
            {"account": acct.id, "amount": "100.00", "idempotency_key": "k2"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        acct.refresh_from_db()
        self.assertEqual(acct.balance, Decimal("1200.0000"))

    @patch("ledger.signals.process_transaction_event.delay")
    def test_transfer_idempotency_replay_success(self, mock_task):
        """Replaying a transfer with the exact same payload returns 201 without duplicate processing."""
        source = AccountFactory(owner_name="Source", balance=Decimal("1000.0000"))
        dest = AccountFactory(owner_name="Dest", balance=Decimal("1000.0000"))
        payload = {
            "source_account": source.id,
            "destination_account": dest.id,
            "amount": "100.00",
            "idempotency_key": "transfer-replay-key",
        }

        # First call
        res1 = self.client.post("/api/transfers/", payload, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Second call (Replay)
        res2 = self.client.post("/api/transfers/", payload, format="json")
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res2.data["id"], res1.data["id"])

        source.refresh_from_db()
        dest.refresh_from_db()
        self.assertEqual(source.balance, Decimal("900.0000"))
        self.assertEqual(dest.balance, Decimal("1100.0000"))

    @patch("ledger.signals.process_transaction_event.delay")
    def test_transfer_idempotency_mismatch_conflict(self, mock_task):
        """Using the same idempotency key for a different transfer payload results in 409."""
        source = AccountFactory(owner_name="Source", balance=Decimal("1000.0000"))
        dest1 = AccountFactory(owner_name="Dest 1", balance=Decimal("1000.0000"))
        dest2 = AccountFactory(owner_name="Dest 2", balance=Decimal("1000.0000"))
        key = "transfer-conflict-key"

        # First call
        self.client.post(
            "/api/transfers/",
            {
                "source_account": source.id,
                "destination_account": dest1.id,
                "amount": "100.00",
                "idempotency_key": key,
            },
            format="json",
        )

        # Second call (Conflict because destination is different)
        res = self.client.post(
            "/api/transfers/",
            {
                "source_account": source.id,
                "destination_account": dest2.id,
                "amount": "100.00",
                "idempotency_key": key,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

        # Second call variant (Conflict because amount is different)
        res_amount = self.client.post(
            "/api/transfers/",
            {
                "source_account": source.id,
                "destination_account": dest1.id,
                "amount": "200.00",
                "idempotency_key": key,
            },
            format="json",
        )
        self.assertEqual(res_amount.status_code, status.HTTP_409_CONFLICT)

        source.refresh_from_db()
        self.assertEqual(
            source.balance, Decimal("900.0000")
        )  # Only the first transfer applied
