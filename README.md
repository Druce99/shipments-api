# Shipment Tracker

Учебный сервис для создания и отслеживания отправлений, изменения их статусов и просмотра истории изменений.

Проект находится в разработке.

## Возможности

- Создание отправлений.
- Изменение статусов отправлений.
- Просмотр истории изменения статусов.
- Сохранение информации в PostgreSQL.
- Использование Kafka для событий отправлений.

## Технологии

- Python 3.13+
- FastAPI
- SQLAlchemy Async
- PostgreSQL 17
- Alembic
- Kafka / aiokafka
- Poetry
- pytest

## Локальный запуск

Понадобятся Python 3.13+, Poetry 2 и запущенный Docker Desktop.
Выполняй команды из каталога `shipments-api`.

### API и PostgreSQL

Если файла `.env` ещё нет, создай его из шаблона командой
`Copy-Item .env.example .env`. PostgreSQL будет доступен на порту `5433`.
Если меняешь пароль в `.env`, обнови его и в `DATABASE_URL`.

```powershell
poetry install
docker compose up -d --wait postgres
poetry run alembic upgrade head
poetry run uvicorn shipments_api.main:app --reload
```

Открой [документацию API](http://127.0.0.1:8000/docs). Там можно создать
отправление, сменить его статус и посмотреть историю.

### Публикация событий в Kafka

Для публикации событий о смене статуса запусти Kafka и relay в отдельном
терминале из того же каталога. Relay читает сохранённые события из
PostgreSQL и отправляет их в Kafka.

```powershell
docker compose -f ../infra/docker-compose.yaml up -d --wait kafka
poetry run python -m shipments_api.relay
```

С настройками из `.env.example` relay подключается к Kafka на
`localhost:9092` и публикует события в топик `shipment-events`.

## Структура проекта

- `src/shipments_api/` — исходный код приложения.
- `tests/` — автоматизированные тесты.
- `migrations/` — миграции Alembic.
- `docs/` — документация проекта.
- `docker-compose.yaml` — конфигурация PostgreSQL.
- `pyproject.toml` — зависимости и настройки инструментов.
- `.env.example` — пример переменных окружения.

## Обработка ошибок API

- **`404 Not Found`** — в базе нет отправления с указанным UUID. Этот статус возвращается при запросе отправления, просмотре его истории или попытке изменить его статус.
- **`409 Conflict`** — отправление существует, но запрошенный переход запрещён для его текущего статуса. Например, из `created` нельзя сразу перейти в `delivered`. Текущий статус и история при этом не меняются.

Оба обработчика возвращают сообщение об ошибке в строковом поле `detail`. Пример ответа `409 Conflict` при переходе из `created` в `delivered`.

```json
{
  "detail": "Shipment status transition from 'created' to 'delivered' is not allowed."
}
```
