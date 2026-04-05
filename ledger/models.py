import uuid

from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, Q
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """Abstract base class for timestamped models."""

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        abstract = True


class Account(TimeStampedModel):
    """
    Represents a financial account belonging to a user.
    A user can have multiple accounts (e.g., in different currencies).
    """

    class AccountType(models.TextChoices):
        CURRENT = "CURRENT", _("Current")
        SAVINGS = "SAVINGS", _("Savings")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ledger_accounts",
        verbose_name=_("user"),
    )
    name = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.CURRENT,
        help_text=_("Type/Label of the account"),
        verbose_name=_("name"),
    )
    balance = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=0,
        help_text=_("Current balance of the account (must be >= 0)"),
        verbose_name=_("balance"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("is active"))

    class Meta:
        constraints = [
            CheckConstraint(check=Q(balance__gte=0), name="balance_not_negative")
        ]
        indexes = [
            models.Index(fields=["is_active"], name="idx_account_active"),
            models.Index(fields=["user", "name"], name="idx_account_user_type"),
            models.Index(fields=["created_at"], name="idx_account_created"),
        ]
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")

    def __str__(self):
        return f"{self.user.username} - {self.name} ({self.balance})"


class Transaction(models.Model):
    """
    Represents a single entry (Credit or Debit) in an account's ledger.
    Transactions are append-only and immutable.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name=_("account"),
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        help_text=_("Positive for Credit (+), Negative for Debit (-)"),
        verbose_name=_("amount"),
    )
    description = models.TextField(blank=True, verbose_name=_("description"))
    idempotency_key = models.UUIDField(
        unique=True,
        null=True,
        blank=True,
        help_text=_("Unique key to prevent duplicate transaction processing"),
        verbose_name=_("idempotency key"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True, editable=False, verbose_name=_("created at")
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"], name="idx_txn_created"),
            models.Index(
                fields=["account", "-created_at"], name="idx_txn_account_created"
            ),
        ]
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")

    def __str__(self):
        type_str = "CREDIT" if self.amount >= 0 else "DEBIT"
        return f"{self.id}: {type_str} {abs(self.amount)} to {self.account.name}"


class Transfer(TimeStampedModel):
    """
    Links two matching transactions together to represent a single money movement
    between two different accounts.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_transaction = models.OneToOneField(
        Transaction,
        on_delete=models.PROTECT,
        related_name="outgoing_transfer",
        verbose_name=_("source transaction"),
    )
    destination_transaction = models.OneToOneField(
        Transaction,
        on_delete=models.PROTECT,
        related_name="incoming_transfer",
        verbose_name=_("destination transaction"),
    )

    class Meta:
        indexes = [
            models.Index(fields=["-created_at"], name="idx_transfer_created"),
        ]
        verbose_name = _("Transfer")
        verbose_name_plural = _("Transfers")

    def __str__(self):
        return f"Transfer {self.id}: From {self.source_transaction.account} to {self.destination_transaction.account}"
