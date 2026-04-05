from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException


class LedgerError(APIException):
    """Base class for all ledger-related exceptions."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("A ledger error occurred.")
    default_code = "ledger_error"


class InsufficientFundsError(LedgerError):
    """Raised when an account does not have enough balance for a debit."""

    default_detail = _("Insufficient funds in the account.")
    default_code = "insufficient_funds"


class AccountInactiveError(LedgerError):
    """Raised when performing operations on an inactive account."""

    default_detail = _("The account is inactive.")
    default_code = "account_inactive"


class InvalidAmountError(LedgerError):
    """Raised when a non-positive amount is used where a positive one is expected."""

    default_detail = _("The amount must be greater than zero.")
    default_code = "invalid_amount"


class TransactionIdempotencyError(LedgerError):
    """Raised when a duplicate idempotency key is detected."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = _("A transaction with this idempotency key already exists.")
    default_code = "duplicate_idempotency_key"
