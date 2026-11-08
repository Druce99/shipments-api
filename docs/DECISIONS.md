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

## Outbox uses its own `BIGINT id`, separate from `event_id`

- Context: the plan used the event id as the outbox primary key. The relay must publish events in the order they were written.
- Decision: `outbox_events.id` is an autoincrement `BIGINT` (publishing order) and `event_id` is a separate unique `UUID` (idempotency key for consumers). No foreign key to `shipments`.
- Alternatives: `id = event_id` (a random UUID has no order); ordering by `created_at` (ties inside one transaction); a foreign key to `shipments` (the outbox would depend on the lifetime of business rows).
- Consequences: deterministic publishing order via a partial index on unpublished rows. The outbox is a self-contained log.

## Store the whole event in `payload`

- Context: `event_id` and `event_type` are also columns of `outbox_events`.
- Decision: `payload` holds the complete event (`model_dump(mode="json")`) and the two columns duplicate fields from it.
- Alternatives: keep only business fields in `payload` and let the relay build the message from the columns (an extra assembly step that can drift).
- Consequences: the Kafka message is self-contained, so a consumer needs nothing else to deduplicate by `event_id` and pick the schema by `event_type` and `event_version`. The columns serve `UNIQUE` and filtering.

## Relay: publish first, mark afterwards, commit per event

- Context: the broker and the database cannot share a transaction.
- Decision: the relay sends an event and waits for the broker acknowledgement, and only then sets `published_at` in its own short transaction.
- Alternatives: mark first and publish later (a crash loses the event); mark the whole batch in one transaction (fewer commits, but a failure repeats more already sent events).
- Consequences: at-least-once delivery. A crash between sending and marking duplicates an event but never loses it, so consumers must be idempotent by `event_id`.

## Run a single relay without `SKIP LOCKED`

- Context: several relays could read the same unpublished rows.
- Decision: run exactly one relay. The read transaction ends before sending, so `FOR UPDATE SKIP LOCKED` would not hold the lock during publishing. With several relays, events of one shipment could also be sent out of order.
- Alternatives: one transaction per batch with `SKIP LOCKED` (long transaction around a network call, more duplicates); shard events by `hash(shipment_id)`; CDC (Debezium).
- Consequences: simple and ordered. Throughput is bounded by one process, which is enough here. Scaling out means sharding by `shipment_id`.

## Use `shipment_id` as the Kafka message key

- Context: Kafka guarantees order only inside a partition.
- Decision: the relay sends each event with `shipment_id` as the key, so all events of one shipment land in one partition in the order they were written.
- Alternatives: no key (round-robin, no order); key by event type (one partition gets all the load).
- Consequences: order per shipment is preserved. Order across different shipments is not guaranteed, and a consumer must not rely on it.

## Hide Kafka behind `EventPublisher` and ignore missing `aiokafka` types

- Context: the relay needs to be tested without a broker, and `aiokafka` ships no `py.typed`, so strict mypy rejects the import.
- Decision: the relay depends on a `Protocol` (`EventPublisher`) declared next to it. `KafkaPublisher` is an adapter over `AIOKafkaProducer` used as an async context manager. `[[tool.mypy.overrides]]` ignores missing imports for `aiokafka.*` only.
- Alternatives: depend on `KafkaPublisher` directly (tests need a broker or `type: ignore`); `AsyncMock` (loses type checking); a per-line `type: ignore`.
- Consequences: relay tests use a simple fake. The producer object is `Any` for mypy, so the adapter is kept thin and verified manually against a real broker.
