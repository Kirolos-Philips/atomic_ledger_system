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
        payload = {"account": acct.id, "amount": "100.00", "idempotency_key": "unique-k"}
        res = self.client.post("/api/transactions/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        acct.refresh_from_db()
        self.assertEqual(acct.balance, Decimal("1100.0000"))

    @patch("ledger.signals.process_transaction_event.delay")
    def test_idempotency_same_payload_replay_success(self, mock_task):
        """Replaying the exact same request payload returns the original result (201)."""
        acct = AccountFactory(owner_name="Idem Use", balance=Decimal("1000.0000"))
        payload = {"account": acct.id, "amount": "100.00", "idempotency_key": "replay-k"}
        
        # First call
        res1 = self.client.post("/api/transactions/", payload, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        
        # Second call (Replay)
        res2 = self.client.post("/api/transactions/", payload, format="json")
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res2.data["id"], res1.data["id"])
        
        acct.refresh_from_db()
        self.assertEqual(acct.balance, Decimal("1100.0000")) # Balance only affected once

    @patch("ledger.signals.process_transaction_event.delay")
    def test_idempotency_mismatch_payload_conflict(self, mock_task):
        """Using the same key for a different payload (mismatched amount) results in 409."""
        acct = AccountFactory(owner_name="Idem Use", balance=Decimal("1000.0000"))
        key = "shared-k"
        
        # First call: $100
        self.client.post("/api/transactions/", 
                         {"account": acct.id, "amount": "100.00", "idempotency_key": key}, 
                         format="json")
        
        # Second call: $200 (Conflict)
        res = self.client.post("/api/transactions/", 
                               {"account": acct.id, "amount": "200.00", "idempotency_key": key}, 
                               format="json")
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        
        acct.refresh_from_db()
        self.assertEqual(acct.balance, Decimal("1100.0000")) # Only first request applied

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
