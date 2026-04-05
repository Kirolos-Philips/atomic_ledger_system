from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ledger", "0002_transaction_type_alter_transaction_idempotency_key_and_more"),
    ]

    operations = [
        # 1. Rename the field from type_ to transaction_type
        migrations.RenameField(
            model_name="transaction",
            old_name="type_",
            new_name="transaction_type",
        ),
        # 2. Rename the index to keep naming consistent
        migrations.RenameIndex(
            model_name="transaction",
            old_name="idx_txn_account_type_created",
            new_name="idx_txn_account_txntype_created",
        ),
    ]
