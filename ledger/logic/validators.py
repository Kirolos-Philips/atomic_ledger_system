from decimal import Decimal

from django.utils.translation import gettext_lazy as _

from ..models import Account, Transaction, Transfer
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
    source_id = getattr(source, "id", source)
    destination_id = getattr(destination, "id", destination)
    if source_id == destination_id:
        raise LedgerError(_("Source and destination accounts must be different."))


def validate_idempotency(
    model_class: Transaction | Transfer,
    idempotency_key: str,
    payload_checks: dict,
    error_message: str = None,
) -> bool:
    """
    Generic idempotency validator.
    payload_checks: dict of {field_name: expected_value}
    Returns True if exists and matches, False if doesn't exist.
    """
    if not idempotency_key:
        return False

    existing = model_class.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        for field, expected_value in payload_checks.items():
            # Handle nested attributes like 'source_transaction.account_id'
            actual_value = existing
            for part in field.split("."):
                actual_value = getattr(actual_value, part)

            if actual_value != expected_value:
                raise TransactionIdempotencyError(
                    error_message
                    or _("Idempotency key exists but request payload does not match.")
                )
    return bool(existing)


def validate_txn_idempotency(
    idempotency_key: str, account_id: int, amount: Decimal
) -> bool:
    return validate_idempotency(
        Transaction,
        idempotency_key,
        {"account_id": account_id, "amount": amount},
    )


def validate_transfer_idempotency(
    idempotency_key: str,
    source_account_id: int,
    destination_account_id: int,
    amount: Decimal,
) -> bool:

    return validate_idempotency(
        Transfer,
        idempotency_key,
        {
            "source_transaction.account_id": source_account_id,
            "destination_transaction.account_id": destination_account_id,
            "amount": amount,
        },
    )
