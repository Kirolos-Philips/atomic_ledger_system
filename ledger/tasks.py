import logging
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _send_transaction_email(user, subject, message):
    """Helper to send an email with error handling."""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info("Email sent to %s: %s", user.email, subject)
    except Exception:
        logger.exception("Failed to send email to %s", user.email)


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
        txn = Transaction.objects.select_related("account__user").get(id=transaction_id)
        user = txn.account.user
        amount = abs(txn.amount).quantize(Decimal("0.0001"))

        logger.info(
            "Transaction event: %s | %s | Account: %s | Amount: %s | User: %s",
            event_type,
            txn.id,
            txn.account.name,
            amount,
            user.username,
        )

        # Send email notification
        if user.email:
            if event_type == "CREDIT":
                subject = f"Deposit Received — {amount}"
                message = (
                    f"Dear {user.get_full_name() or user.username},\n\n"
                    f"A deposit of {amount} has been credited to your "
                    f"{txn.account.get_name_display()} account.\n\n"
                    f"New Balance: {txn.account.balance.quantize(Decimal('0.0001'))}\n\n"
                    f"Transaction ID: {txn.id}\n"
                    f"Description: {txn.description or 'N/A'}\n\n"
                    f"— Atomic Ledger"
                )
            else:
                subject = f"Withdrawal Processed — {amount}"
                message = (
                    f"Dear {user.get_full_name() or user.username},\n\n"
                    f"A withdrawal of {amount} has been debited from your "
                    f"{txn.account.get_name_display()} account.\n\n"
                    f"New Balance: {txn.account.balance.quantize(Decimal('0.0001'))}\n\n"
                    f"Transaction ID: {txn.id}\n"
                    f"Description: {txn.description or 'N/A'}\n\n"
                    f"— Atomic Ledger"
                )

            _send_transaction_email(user, subject, message)

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
            "source_transaction__account__user",
            "destination_transaction__account__user",
        ).get(id=transfer_id)

        src_txn = transfer.source_transaction
        dst_txn = transfer.destination_transaction
        src_user = src_txn.account.user
        dst_user = dst_txn.account.user
        amount = abs(src_txn.amount).quantize(Decimal("0.0001"))

        logger.info(
            "Transfer event: %s | %s (%s) → %s (%s) | Amount: %s",
            transfer.id,
            src_txn.account.name,
            src_user.username,
            dst_txn.account.name,
            dst_user.username,
            amount,
        )

        # --- Email to Sender ---
        if src_user.email:
            _send_transaction_email(
                src_user,
                subject=f"Transfer Sent — {amount}",
                message=(
                    f"Dear {src_user.get_full_name() or src_user.username},\n\n"
                    f"You have successfully transferred {amount} "
                    f"from your {src_txn.account.get_name_display()} account "
                    f"to {dst_user.get_full_name() or dst_user.username}.\n\n"
                    f"New Balance: {src_txn.account.balance.quantize(Decimal('0.0001'))}\n\n"
                    f"Transfer ID: {transfer.id}\n"
                    f"Description: {src_txn.description or 'N/A'}\n\n"
                    f"— Atomic Ledger"
                ),
            )

        # --- Email to Receiver ---
        if dst_user.email:
            _send_transaction_email(
                dst_user,
                subject=f"Transfer Received — {amount}",
                message=(
                    f"Dear {dst_user.get_full_name() or dst_user.username},\n\n"
                    f"You have received a transfer of {amount} "
                    f"into your {dst_txn.account.get_name_display()} account "
                    f"from {src_user.get_full_name() or src_user.username}.\n\n"
                    f"New Balance: {dst_txn.account.balance.quantize(Decimal('0.0001'))}\n\n"
                    f"Transfer ID: {transfer.id}\n"
                    f"Description: {dst_txn.description or 'N/A'}\n\n"
                    f"— Atomic Ledger"
                ),
            )

    except Transfer.DoesNotExist:
        logger.error("Transfer %s not found", transfer_id)
    except Exception as exc:
        logger.exception("Failed to process transfer event %s", transfer_id)
        raise self.retry(exc=exc)
