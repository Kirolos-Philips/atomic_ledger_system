import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Transaction, Transfer
from .tasks import process_transaction_event, process_transfer_event

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Transaction)
def on_transaction_created(sender, instance, created, **kwargs):
    """
    Fires a Celery task after a new Transaction is saved.
    Uses transaction.on_commit to ensure the task is only dispatched
    after the database transaction is successfully committed.
    """
    if not created:
        return

    transaction.on_commit(
        lambda: process_transaction_event.delay(
            transaction_id=str(instance.id),
            event_type=instance.transaction_type,
        )
    )


@receiver(post_save, sender=Transfer)
def on_transfer_created(sender, instance, created, **kwargs):
    """
    Fires a Celery task after a new Transfer is saved.
    Uses transaction.on_commit to ensure the task is only dispatched
    after the database transaction is successfully committed.
    """
    if not created:
        return

    transaction.on_commit(
        lambda: process_transfer_event.delay(
            transfer_id=str(instance.id),
        )
    )
