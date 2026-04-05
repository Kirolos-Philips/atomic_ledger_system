from decimal import Decimal

from django.utils.translation import gettext_lazy as _

from ..models import Account
from .exceptions import (
    AccountInactiveError,
    InsufficientFundsError,
    LedgerError,
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
