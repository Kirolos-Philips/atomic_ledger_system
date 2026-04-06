from decimal import Decimal

from django.utils.translation import gettext_lazy as _

from ..models import Account, Transaction
from .exceptions import (
    AccountInactiveError,
    InsufficientFundsError,
    LedgerError,
    TransactionIdempotencyError,
)


def validate_account_active(account: Account):
    if not account.is_active:
        raise AccountInactiveError()


def validate_sufficient_funds(account: Account, amount: Decimal):
    """Checks if an account has enough balance for a debit (amount must be negative)."""
    if amount < 0 and (account.balance + amount) < 0:
        raise InsufficientFundsError()


def validate_transfer_accounts(source: Account, destination: Account):
    if source.id == destination.id:
        raise LedgerError(_("Source and destination accounts must be different."))


def validate_idempotency(idempotency_key: str, account_id: int, amount: Decimal):
    """
    Checks if an idempotency key exists and verifies if the payload matches.
    If key exists but payload is different, raises TransactionIdempotencyError.
    """
    if not idempotency_key:
        return

    existing = Transaction.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if existing.account_id != account_id or existing.amount != amount:
            raise TransactionIdempotencyError(
                _("Idempotency key exists but request payload does not match.")
            )
