from rest_framework import serializers

from .logic.services import create_transaction, create_transfer
from .logic.validators import (
    validate_account_active,
    validate_sufficient_funds,
    validate_transfer_accounts,
)
from .models import Account, Transaction, Transfer


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id", "user", "name", "balance", "is_active", "created_at"]
        read_only_fields = ["id", "balance", "created_at"]


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            "id",
            "account",
            "type_",
            "amount",
            "description",
            "idempotency_key",
            "created_at",
        ]
        read_only_fields = ["id", "type_", "created_at"]

    def validate(self, data):
        account = data["account"]
        amount = data["amount"]
        validate_account_active(account)
        validate_sufficient_funds(account, amount)
        return data

    def create(self, validated_data):
        # We use our service for creation to ensure safety
        return create_transaction(
            account_id=validated_data["account"].id,
            amount=validated_data["amount"],
            description=validated_data.get("description", ""),
            idempotency_key=validated_data.get("idempotency_key"),
        )


class TransferSerializer(serializers.ModelSerializer):
    source_account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(), write_only=True
    )
    destination_account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(), write_only=True
    )
    amount = serializers.DecimalField(max_digits=20, decimal_places=4, min_value=0.01)
    description = serializers.CharField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(required=False, allow_null=True)

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

        # 3. Source must have funds
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
