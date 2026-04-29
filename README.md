# DocuChat-Py

An AI-powered document chatbot built with FastAPI, SQLModel, and `fastapi-events`.

## Features

- **Asynchronous Architecture**: Fully async database operations using `aiosqlite`.
- **Authentication**: JWT-based auth with access and refresh tokens.
- **Event-Driven**: Post-registration triggers via `fastapi-events`.
- **Background Processing**: Asynchronous document processing using Celery backed by Redis.
- **Task Monitoring**: Web-based monitoring for Celery tasks via Flower.
- **Standardized API Responses**: Consistent success and error shapes across all endpoints.
- **Automated CI**: GitHub Actions integration for linting, formatting, and testing.

## Getting Started

### Prerequisites

- Python 3.12+
- `uv` (modern Python package manager)

### Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Set up your `.env` file (see `config.py` for required variables).

### Running the Application

1. Ensure your Redis server is running (check `REDIS_URL` in `.env`).
2. Start the Celery worker for background document processing:
   ```bash
   uv run celery -A queues.celery_task.app worker --loglevel=info
   ```
3. Start the FastAPI development server:
   ```bash
   uv run fastapi dev
   ```
4. (Optional) Start the Flower dashboard to monitor Celery tasks:
   ```bash
   uv run celery -A queues.celery_task.app flower
   ```
   The dashboard will be available at `http://localhost:5555`.

### Running Tests

```bash
uv run pytest
```

### Linting and Formatting

```bash
uv run ruff check .
uv run ruff format .
```

## API Response Format

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": []
  }
}
```

## Project Structure

- `api/v1/`: API route definitions.
- `auth/`: Authentication logic and dependencies.
- `events/`: Event handlers for asynchronous background tasks.
- `middleware/`: Custom middlewares (logging, exception handling).
- `schemas/`: Pydantic models for request/response validation.
- `models.py`: Database models.
- `dbmanager.py`: Async database manager and session handling.
