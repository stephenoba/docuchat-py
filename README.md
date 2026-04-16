# docuchat-py
A simple fastapi, AI powered document chatbot.


## Installation

using uv

```bash
uv pip install -r requirements/local.txt
```

## Running

```bash
fastapi dev main.py
```

## Migrations

### Create a migration

```bash
alembic revision --autogenerate -m "Initial migrations"
```

### Upgrade to latest migration

```bash
alembic upgrade head
```
