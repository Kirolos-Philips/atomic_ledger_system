from decimal import Decimal

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import filters, mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Account, Transaction, Transfer
from .serializers import (
    AccountSerializer,
    TransactionSerializer,
    TransferSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary="List all accounts",
        description="Returns a paginated list of all accounts the current user has access to. "
        "Supports filtering by `is_active` and `user`, and search by `name`.",
    ),
    retrieve=extend_schema(
        summary="Retrieve account details",
        description="Returns the full details of a specific account including its current balance.",
    ),
    create=extend_schema(
        summary="Create a new account",
        description="Creates a new financial account for the authenticated user.",
    ),
    update=extend_schema(
        summary="Update an account",
        description="Fully updates an existing account. Balance cannot be modified directly.",
    ),
    partial_update=extend_schema(
        summary="Partially update an account",
        description="Partially updates an existing account (e.g., toggle `is_active`).",
    ),
    destroy=extend_schema(
        summary="Deactivate an account",
        description="Deletes an account. Accounts with transactions cannot be deleted due to PROTECT constraints.",
    ),
)
class AccountViewSet(viewsets.ModelViewSet):
    """Manage customer financial accounts."""

    queryset = Account.objects.all().order_by("-created_at")
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["is_active", "user"]
    search_fields = ["name"]

    @extend_schema(
        summary="Get account balance",
        description="Returns only the current balance of the specified account. "
        "Useful for quick balance checks without loading full account details.",
        responses={
            200: {
                "type": "object",
                "properties": {"balance": {"type": "string", "example": "1500.0000"}},
            }
        },
    )
    @action(detail=True, methods=["get"], url_path="balance")
    def balance(self, request, pk=None):
        """Returns the current balance of the account."""
        account = self.get_object()
        return Response({"balance": str(account.balance.quantize(Decimal("0.0001")))})


@extend_schema_view(
    list=extend_schema(
        summary="List transactions",
        description="Returns a paginated list of all ledger transactions. "
        "Filter by `account`, `type_` (DEBIT/CREDIT), or `idempotency_key`.",
    ),
    retrieve=extend_schema(
        summary="Retrieve a transaction",
        description="Returns the full details of a specific transaction.",
    ),
    create=extend_schema(
        summary="Create a transaction",
        description="Creates a new credit or debit entry on the specified account. "
        "The `type_` field is automatically determined from the sign of `amount`. "
        "Uses row-level locking (`SELECT FOR UPDATE`) to ensure consistency under concurrent access. "
        "**Positive amount** = Credit, **Negative amount** = Debit.",
        examples=[
            OpenApiExample(
                "Credit (Deposit)",
                value={
                    "account": "550e8400-e29b-41d4-a716-446655440000",
                    "amount": "500.00",
                    "description": "Salary deposit",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Debit (Withdrawal)",
                value={
                    "account": "550e8400-e29b-41d4-a716-446655440000",
                    "amount": "-100.00",
                    "description": "ATM withdrawal",
                },
                request_only=True,
            ),
        ],
    ),
)
class TransactionViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Append-only ledger transactions.

    Transactions are **immutable** — once created, they cannot be updated or deleted.
    This ensures a complete and auditable financial trail.
    """

    queryset = Transaction.objects.select_related("account").order_by("-created_at")
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["account", "transaction_type"]
    search_fields = ["description", "idempotency_key"]


@extend_schema_view(
    list=extend_schema(
        summary="List transfers",
        description="Returns a paginated list of all transfers between accounts.",
    ),
    retrieve=extend_schema(
        summary="Retrieve a transfer",
        description="Returns the full details of a specific transfer, including linked source and destination transactions.",
    ),
    create=extend_schema(
        summary="Create a transfer",
        description="Atomically moves money between two accounts. "
        "This creates two linked transactions: a **debit** on the source account and a **credit** on the destination. "
        "Both accounts must be active and the source must have sufficient funds. "
        "The entire operation is wrapped in a database transaction with row-level locking.",
        examples=[
            OpenApiExample(
                "Transfer between accounts",
                value={
                    "source_account": "550e8400-e29b-41d4-a716-446655440000",
                    "destination_account": "660e8400-e29b-41d4-a716-446655440001",
                    "amount": "250.00",
                    "description": "Rent payment",
                },
                request_only=True,
            ),
        ],
    ),
)
class TransferViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Atomic money transfers between accounts.

    Transfers are **immutable** — once created, they cannot be updated or deleted.
    Each transfer links exactly two transactions (source debit + destination credit).
    """

    queryset = Transfer.objects.select_related(
        "source_transaction__account",
        "destination_transaction__account",
    ).order_by("-created_at")
    serializer_class = TransferSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "source_transaction__account",
        "destination_transaction__account",
    ]
