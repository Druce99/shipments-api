# Decision log: shipments-api

## Fetch server-generated `updated_at` with `eager_defaults`

- Context: `updated_at` is set by the database (`onupdate=func.now()`). After an `UPDATE`, SQLAlchemy marks it as expired and reloads it lazily. In async code that implicit load raised `MissingGreenlet` while building `ShipmentRead` in `PATCH /status`.
- Decision: set `__mapper_args__ = {"eager_defaults": True}` on `Shipment`. SQLAlchemy then adds `RETURNING` to `INSERT` and `UPDATE`, so PostgreSQL returns the new server values in the same statement.
- Alternatives: call `session.refresh(shipment)` after each change (works, but costs an extra `SELECT` and is easy to forget); compute `updated_at` in Python (the clock would move out of the database and could differ between app instances).
- Consequences: no extra query and no lazy load. The setting applies to every write of `Shipment` and relies on `RETURNING`, which PostgreSQL supports.

## Order status history by `id`, not by `created_at`

- Context: `now()` returns the transaction start time, so rows written in one transaction get the same `created_at` (for example the shipment and its first history row). Sorting by it gives no stable order.
- Decision: order `status_history` by its autoincrement `id` and keep an index on `(shipment_id, id)`. Writes to one shipment are serialized by `SELECT ... FOR UPDATE`, so `id` order equals the real order of changes.
- Alternatives: `ORDER BY created_at` (ties, nondeterministic); `clock_timestamp()` (real time, but the clock can go backwards and it is not guaranteed to be unique).
- Consequences: deterministic order and a query served by one index. `created_at` is informational only. Ids can have gaps (rolled-back transactions), which does not matter for ordering.

## Keep `current_status` on `shipments` next to `status_history`

- Context: the history already contains the latest status, but reading the list and filtering by status must be fast.
- Decision: store `current_status` in `shipments` (deliberate denormalization) and append every change to `status_history`. Both are written in one transaction after locking the shipment row.
- Alternatives: derive the current status from the last history row on every read (no duplication, but a join or subquery for each read and filter); store only `shipments` without history (loses the audit trail).
- Consequences: fast reads and a simple status filter. The two places must stay consistent; the service guarantees it with one transaction (covered by rollback tests), the database does not enforce it.

## Look up a shipment only by internal id (tracking-number search deferred)

- Context: the API addresses a shipment by its UUID, while a customer knows only the tracking number. Search by tracking number is not part of the five endpoints in the plan.
- Decision: defer it. Revisit together with the client role (JWT and roles).
- Alternatives: a `tracking_number` filter on `GET /shipments` (the unique index already exists); a separate `/by-tracking/{number}` path.
- Consequences: known limitation. Operators work with ids; the filter option is the likely first choice later.
