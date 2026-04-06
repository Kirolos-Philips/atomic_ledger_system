# Atomic Ledger System

A high-performance, atomic financial ledger system built with Django, DRF, and Celery.

## 🚀 Getting Started

1. **Start infrastructure**: `make docker-up`
2. **Setup DB**: `make docker-migrate`
3. **Run Tests**: `make docker-test`
4. **Docs**: visit `http://localhost:8000/api/docs/`



## 📁 Project Structure

```text
atomic_ledger_system/
├── config/              # Django settings, Celery app
├── docker/              # Dockerfiles and infrastructure configs
├── ledger/
│   ├── logic/           # Core Business Logic (Services, Exceptions)
│   ├── tests/           # API Tests (Factories, Parameterized cases)
│   ├── models.py        # Database entities (Account, Transaction, Transfer)
│   ├── signals.py       # Post-save event hooks
│   ├── tasks.py         # Asynchronous Celery tasks
│   └── views.py         # DRF ViewSets with Swagger documentation
├── Makefile             # Main developer shortcuts
└── Makefile.prod        # Production deployment shortcuts
```

## 🛠 Makefile Commands

| Category | Command | Description |
|---|---|---|
| **Docker** | `make docker-up` | Start all services in the background |
| | `make docker-down` | Stop and remove all containers |
| | `make docker-build` | Rebuild Docker images |
| | `make docker-logs` | Tail container logs |
| | `make docker-shell` | Open a bash shell inside the web container |
| **Ledger DB** | `make docker-migrate` | Run Django migrations inside Docker |
| | `make docker-makemigrations` | Create new migrations based on model changes |
| **Testing** | `make docker-test` | Run all test cases inside Docker (preserves DB) |
| | `make test` | Run tests locally (requires local env) |
| **I18n** | `make docker-makemessages` | Extract translation strings (Default L=ar) |
| | `make docker-compilemessages` | Compile .po files to .mo inside Docker |
| **Maintenance** | `make lint` / `make format` | Check/fix code style using Ruff |
| | `make check` | Run Django system health checks |

## 🛤 Available Endpoints

- **Swagger UI**: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- **ReDoc**: [http://localhost:8000/api/redoc/](http://localhost:8000/api/redoc/)

## 🛡 Internal Design: Atomicity & Consistency

- **Atomicity**: Handled via `transaction.atomic` in the service layer. Transfers are all-or-nothing.
- **Consistency**: PostgreSQL row-level locks (`SELECT FOR UPDATE`) prevent double-spending in concurrent scenarios.
- **Integrity**: DB `CHECK` prevents negative balances (`balance >= 0`).

## 🔑 Idempotency & Payload Matching

The system uses a robust idempotency mechanism via `idempotency_key` in request payloads:
- **Success Replays**: If the same key is submitted with the **matching payload** (amount, account), the system returns the existing transaction (201 Created) without duplicating the financial impact.
- **Conflict Rejection**: If the same key is submitted with a **different payload**, the system returns a `409 Conflict`.
- **Implementation Note**: The key resides in the `Transaction` model rather than `Transfer`. This ensures all financial movements are protected. Transfers generate derived keys (`DR-{key}` and `CR-{key}`) for the underlying debit and credit transactions.

## ⚖️ Tradeoffs & Recent Refactoring

- **No-Auth Architecture**: Authentication has been removed as per core requirements to allow public service access.
- **Integer IDs**: Reverted from UUIDs to standard `BigAutoField` (Integer) for improved operational efficiency and matching external requirements.
- **Environment Management**: Switched to `django-environ` for unified configuration via `.env` files.
- **Pagination**: `PageNumberPagination` for simpler test integration.
- **Retries**: Basic retry on task failure (3 retries).

## 📈 Future Improvements

1. **Deadlock-Proof Locking**: Implement deterministic locking order (ID sorting) for multi-account transfers to prevent circular wait conditions.
2. **Distributed Idempotency (Redis)**: Offload `idempotency_key` checks to Redis for sub-millisecond lookups and better protection against high-concurrency race conditions.
3. **Immutable Audit Vault**: Implement a separate, append-only audit log for all ledger movements to ensure regulatory compliance.
4. **Property-Based Testing (Hypothesis)**: Use random edge-case generation to verify ledger invariants (e.g., total balance conservation).
5. **Adaptive Rate Limiting**: Implement API throttling to protect against automated abuse and ensure system stability under heavy load.

