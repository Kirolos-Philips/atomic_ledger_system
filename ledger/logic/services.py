from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from ..models import Account, Transaction, Transfer
from .exceptions import (
    InvalidAmountError,
    LedgerError,
)
from .validators import (
    validate_account_active,
    validate_sufficient_funds,
)


def create_transaction(
    account_id: int,
    amount: Decimal,
    description: str = "",
    idempotency_key: Optional[str] = None,
) -> Transaction:
    """
    Creates a single transaction (Credit or Debit) for an account.
    A positive amount is a Credit, a negative amount is a Debit.
    Uses SELECT FOR UPDATE to prevent race conditions during balance checks.
    """
    if amount == 0:
        raise InvalidAmountError()

    with transaction.atomic():
        # 1. Lock the account row for the duration of the transaction
        account = Account.objects.select_for_update().get(id=account_id)

        # 2. Business Validations
        validate_account_active(account)
        validate_sufficient_funds(account, amount)

        # 3. Check for idempotency key if provided
        if idempotency_key:
            existing_txn = Transaction.objects.filter(
                idempotency_key=idempotency_key
            ).first()
            if existing_txn:
                # If we got here, the serializer already validated the payload (account/amount)
                # so we can safely return the existing record for a "Success Replay"
                return existing_txn

        # 4. Create the transaction record
        txn_type = (
            Transaction.TransactionType.CREDIT
            if amount > 0
            else Transaction.TransactionType.DEBIT
        )
        txn = Transaction.objects.create(
            account=account,
            transaction_type=txn_type,
            amount=amount,
            description=description,
            idempotency_key=idempotency_key,
        )

        # 5. Update the account balance
        account.balance += amount
        account.save(update_fields=["balance", "updated_at"])

        return txn


def create_transfer(
    source_account_id: int,
    destination_account_id: int,
    amount: Decimal,
    description: str = "",
    idempotency_key: Optional[str] = None,
) -> Transfer:
    """
    Moves money between two accounts atomically.
    Creates a Source Debit and a Destination Credit linked by a Transfer record.
    """
    if amount <= 0:
        raise InvalidAmountError()

    # (Early check, final check happens inside create_transaction via validators)
    # Note: We need a temporary check here or just allow create_transaction to handle it.
    # To be explicit and consistent with original logic:
    if source_account_id == destination_account_id:
        raise LedgerError(_("Source and destination accounts must be different."))

    with transaction.atomic():
        # 1. Create the source debit transaction
        source_txn = create_transaction(
            account_id=source_account_id,
            amount=-amount,
            description=description or f"Transfer to {destination_account_id}",
            idempotency_key=f"DR-{idempotency_key}" if idempotency_key else None,
        )

        # 2. Create the destination credit transaction
        dest_txn = create_transaction(
            account_id=destination_account_id,
            amount=amount,
            description=description or f"Transfer from {source_account_id}",
            idempotency_key=f"CR-{idempotency_key}" if idempotency_key else None,
        )

        # 3. Create the transfer record to link them
        transfer = Transfer.objects.create(
            source_transaction=source_txn, destination_transaction=dest_txn
        )

        return transfer
