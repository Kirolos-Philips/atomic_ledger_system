from django.contrib import admin

from .models import Account, Transaction, Transfer


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner_name",
        "account_type",
        "currency",
        "balance",
        "is_active",
        "created_at",
    )
    list_filter = ("account_type", "is_active", "currency")
    search_fields = ("id", "owner_name", "account_type")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "account",
        "transaction_type",
        "amount",
        "created_at",
        "idempotency_key",
    )
    list_filter = ("transaction_type", "created_at")
    search_fields = ("id", "account__account_type", "description", "idempotency_key")
    fields = [
        "id",
        "account",
        "transaction_type",
        "amount",
        "description",
        "idempotency_key",
        "created_at",
    ]
    readonly_fields = ("id", "transaction_type", "created_at")

    def has_change_permission(self, request, obj=None):
        """Transactions are immutable and cannot be modified."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Transactions are append-only and cannot be deleted."""
        return False


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ("id", "source_transaction", "destination_transaction", "created_at")
    readonly_fields = ("id", "created_at", "updated_at")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
