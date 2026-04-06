import logging
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _send_transaction_email(email, subject, message):
    """Helper to send an email with error handling."""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info("Email sent to %s: %s", email, subject)
    except Exception:
        logger.exception("Failed to send email to %s", email)


@shared_task(
    bind=True,
    name="ledger.process_transaction_event",
    max_retries=3,
    default_retry_delay=5,
)
def process_transaction_event(self, transaction_id: str, event_type: str):
    """
    Processes a transaction event asynchronously:
    1. Logs the event
    2. Sends an email notification to the account holder
    """
    from ledger.models import Transaction

    try:
        txn = Transaction.objects.select_related("account").get(id=transaction_id)
        account = txn.account
        amount = abs(txn.amount).quantize(Decimal("0.0001"))

        logger.info(
            "Transaction event: %s | %s | Account: %s | Amount: %s | Owner: %s",
            event_type,
            txn.id,
            account.account_type,
            amount,
            account.owner_name,
        )

        # Send email notification
        if account.user_email:
            if event_type == "CREDIT":
                subject = f"Deposit Received — {amount}"
                message = (
                    f"Dear {account.owner_name},\n\n"
                    f"A deposit of {amount} has been credited to your "
                    f"{account.get_account_type_display()} account.\n\n"
                    f"New Balance: {account.balance.quantize(Decimal('0.0001'))}\n\n"
                    f"Transaction ID: {txn.id}\n"
                    f"Description: {txn.description or 'N/A'}\n\n"
                    f"— Atomic Ledger"
                )
            else:
                subject = f"Withdrawal Processed — {amount}"
                message = (
                    f"Dear {account.owner_name},\n\n"
                    f"A withdrawal of {amount} has been debited from your "
                    f"{account.get_account_type_display()} account.\n\n"
                    f"New Balance: {account.balance.quantize(Decimal('0.0001'))}\n\n"
                    f"Transaction ID: {txn.id}\n"
                    f"Description: {txn.description or 'N/A'}\n\n"
                    f"— Atomic Ledger"
                )

            _send_transaction_email(account.user_email, subject, message)

    except Transaction.DoesNotExist:
        logger.error(
            "Transaction %s not found for event %s", transaction_id, event_type
        )
    except Exception as exc:
        logger.exception("Failed to process transaction event %s", transaction_id)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="ledger.process_transfer_event",
    max_retries=3,
    default_retry_delay=5,
)
def process_transfer_event(self, transfer_id: str):
    """
    Processes a transfer event asynchronously:
    1. Logs the event
    2. Sends email notifications to both sender and receiver
    """
    from ledger.models import Transfer

    try:
        transfer = Transfer.objects.select_related(
            "source_transaction__account",
            "destination_transaction__account",
        ).get(id=transfer_id)

        src_account = transfer.source_transaction.account
        dst_account = transfer.destination_transaction.account
        amount = abs(transfer.source_transaction.amount).quantize(Decimal("0.0001"))

        logger.info(
            "Transfer event: %s | %s (%s) → %s (%s) | Amount: %s",
            transfer.id,
            src_account.account_type,
            src_account.owner_name,
            dst_account.account_type,
            dst_account.owner_name,
            amount,
        )

        # --- Email to Sender ---
        if src_account.user_email:
            _send_transaction_email(
                src_account.user_email,
                subject=f"Transfer Sent — {amount}",
                message=(
                    f"Dear {src_account.owner_name},\n\n"
                    f"You have successfully transferred {amount} "
                    f"from your {src_account.get_account_type_display()} account "
                    f"to {dst_account.owner_name}.\n\n"
                    f"New Balance: {src_account.balance.quantize(Decimal('0.0001'))}\n\n"
                    f"Transfer ID: {transfer.id}\n"
                    f"Description: {transfer.source_transaction.description or 'N/A'}\n\n"
                    f"— Atomic Ledger"
                ),
            )

        # --- Email to Receiver ---
        if dst_account.user_email:
            _send_transaction_email(
                dst_account.user_email,
                subject=f"Transfer Received — {amount}",
                message=(
                    f"Dear {dst_account.owner_name},\n\n"
                    f"You have received a transfer of {amount} "
                    f"into your {dst_account.get_account_type_display()} account "
                    f"from {src_account.owner_name}.\n\n"
                    f"New Balance: {dst_account.balance.quantize(Decimal('0.0001'))}\n\n"
                    f"Transfer ID: {transfer.id}\n"
                    f"Description: {transfer.source_transaction.description or 'N/A'}\n\n"
                    f"— Atomic Ledger"
                ),
            )

    except Transfer.DoesNotExist:
        logger.error("Transfer %s not found", transfer_id)
    except Exception as exc:
        logger.exception("Failed to process transfer event %s", transfer_id)
        raise self.retry(exc=exc)
