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
    Represents a financial account belonging to a customer.
    Customers can have multiple accounts (e.g., in different currencies).
    """

    class AccountType(models.TextChoices):
        CURRENT = "CURRENT", _("Current")
        SAVINGS = "SAVINGS", _("Savings")

    class Currency(models.TextChoices):
        USD = "USD", _("US Dollar")
        EUR = "EUR", _("Euro")
        GBP = "GBP", _("British Pound")
        EGP = "EGP", _("Egyptian Pound")

    owner_name = models.CharField(
        max_length=255,
        verbose_name=_("owner name"),
    )
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.CURRENT,
        help_text=_("Type/Label of the account"),
        verbose_name=_("account type"),
    )
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.USD,
        help_text=_("Currency code (e.g., USD, EUR)"),
        verbose_name=_("currency"),
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
            models.Index(fields=["owner_name"], name="idx_account_owner"),
            models.Index(fields=["created_at"], name="idx_account_created"),
        ]
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")

    def __str__(self):
        return (
            f"{self.owner_name} - {self.account_type} ({self.currency} {self.balance})"
        )

    @property
    def user_email(self):
        """Dynamic placeholder email derived from owner_name."""
        username = self.owner_name.replace(" ", "_")
        return f"{username}@test.com"


class Transaction(models.Model):
    """
    Represents a single entry (Credit or Debit) in an account's ledger.
    Transactions are append-only and immutable.
    """

    class TransactionType(models.TextChoices):
        DEBIT = "DEBIT", _("Debit")
        CREDIT = "CREDIT", _("Credit")

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name=_("account"),
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices,
        verbose_name=_("type"),
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        help_text=_("Positive for Credit (+), Negative for Debit (-)"),
        verbose_name=_("amount"),
    )
    description = models.TextField(blank=True, verbose_name=_("description"))
    idempotency_key = models.CharField(
        max_length=255,
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
            models.Index(
                fields=["account", "transaction_type", "-created_at"],
                name="idx_txn_account_type_created",
            ),
        ]
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")

    def __str__(self):
        return f"{self.pk}: {self.transaction_type} {abs(self.amount)} to {self.account.account_type}"


class Transfer(TimeStampedModel):
    """
    Links two matching transactions together to represent a single money movement
    between two different accounts.
    """

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
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        help_text=_("Amount transferred (must be > 0)"),
        verbose_name=_("amount"),
        null=True,  # Allow null temporarily for migration of existing records if any
    )
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text=_("Unique key to prevent duplicate transfer processing"),
        verbose_name=_("idempotency key"),
    )

    class Meta:
        constraints = [
            CheckConstraint(check=Q(amount__gt=0), name="transfer_amount_positive")
        ]
        indexes = [
            models.Index(fields=["-created_at"], name="idx_transfer_created"),
        ]
        verbose_name = _("Transfer")
        verbose_name_plural = _("Transfers")

    def __str__(self):
        return f"Transfer {self.id}: From {self.source_transaction.account} to {self.destination_transaction.account}"
