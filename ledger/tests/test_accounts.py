from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from .factories import AccountFactory, TokenFactory, UserFactory


class AccountTests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        token = TokenFactory(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_create_and_balance(self):
        res = self.client.post(
            "/api/accounts/",
            {"name": "CURRENT", "user": self.user.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["balance"], "0.0000")

        bal = self.client.get(f"/api/accounts/{res.data['id']}/balance/")
        self.assertEqual(bal.data["balance"], "0.0000")

    def test_validation_and_read_only_balance(self):
        """Invalid type is rejected; balance cannot be modified via API."""
        invalid = self.client.post(
            "/api/accounts/",
            {"name": "INVALID", "user": self.user.id},
            format="json",
        )
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

        account = AccountFactory(user=self.user, balance=Decimal("500.0000"))
        self.client.patch(
            f"/api/accounts/{account.id}/",
            {"balance": "99999"},
            format="json",
        )
        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal("500.0000"))

    def test_unauthenticated_access_denied(self):
        self.client.credentials()
        res = self.client.get("/api/accounts/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
