from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from rest_framework import serializers

from .logic.services import create_transaction, create_transfer
from .logic.validators import (
    validate_account_active,
    validate_sufficient_funds,
    validate_transfer_accounts,
)
from .models import Account, Transaction, Transfer


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Account Response",
            value={
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user": 1,
                "name": "CURRENT",
                "balance": "1500.0000",
                "is_active": True,
                "created_at": "2026-04-05T22:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id", "user", "name", "balance", "is_active", "created_at"]
        read_only_fields = ["id", "balance", "created_at"]


class TransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "account",
            "account_name",
            "transaction_type",
            "amount",
            "description",
            "idempotency_key",
            "created_at",
        ]
        read_only_fields = ["id", "transaction_type", "account_name", "created_at"]

    def validate(self, data):
        account = data["account"]
        amount = data["amount"]
        validate_account_active(account)
        validate_sufficient_funds(account, amount)
        return data

    def create(self, validated_data):
        return create_transaction(
            account_id=validated_data["account"].id,
            amount=validated_data["amount"],
            description=validated_data.get("description", ""),
            idempotency_key=validated_data.get("idempotency_key"),
        )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Transfer Request",
            value={
                "source_account": "550e8400-e29b-41d4-a716-446655440000",
                "destination_account": "660e8400-e29b-41d4-a716-446655440001",
                "amount": "250.0000",
                "description": "Rent payment",
            },
            request_only=True,
        ),
    ]
)
class TransferSerializer(serializers.ModelSerializer):
    source_account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(), write_only=True
    )
    destination_account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(), write_only=True
    )
    amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=4,
        min_value=0.01,
        help_text="Amount to transfer (must be > 0).",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional note for the transfer.",
    )
    idempotency_key = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Unique key to prevent duplicate transfer processing.",
    )

    class Meta:
        model = Transfer
        fields = [
            "id",
            "source_account",
            "destination_account",
            "amount",
            "description",
            "idempotency_key",
            "source_transaction",
            "destination_transaction",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "source_transaction",
            "destination_transaction",
            "created_at",
        ]

    def validate(self, data):
        source_account = data["source_account"]
        destination_account = data["destination_account"]
        amount = data["amount"]

        # 1. Accounts must be different
        validate_transfer_accounts(source_account, destination_account)

        # 2. Both accounts must be active
        validate_account_active(source_account)
        validate_account_active(destination_account)

        # 3. Source must have sufficient funds
        validate_sufficient_funds(source_account, -amount)

        return data

    def create(self, validated_data):
        return create_transfer(
            source_account_id=validated_data["source_account"].id,
            destination_account_id=validated_data["destination_account"].id,
            amount=validated_data["amount"],
            description=validated_data.get("description", ""),
            idempotency_key=validated_data.get("idempotency_key"),
        )
