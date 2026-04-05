from django.contrib import admin

from .models import Account, Transaction, Transfer


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "name", "balance", "is_active", "created_at")
    list_filter = ("name", "is_active", "user")
    search_fields = ("id", "user__username", "name")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "account", "type_", "amount", "created_at", "idempotency_key")
    list_filter = ("type_", "created_at")
    search_fields = ("id", "account__name", "description", "idempotency_key")
    fields = [
        "id",
        "account",
        "type_",
        "amount",
        "description",
        "idempotency_key",
        "created_at",
    ]
    readonly_fields = ("id", "type_", "created_at")

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
