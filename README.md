# DocuChat-Py

An AI-powered document chatbot built with FastAPI, SQLModel, and `fastapi-events`.

## Features

- **Asynchronous Architecture**: Fully async database operations using `SQLModel` and `SQLAlchemy`.
- **Authentication**: JWT-based auth with access and refresh tokens.
- **Event-Driven**: Post-registration triggers and document processing via `fastapi-events`.
- **Background Processing**: Asynchronous document processing using Celery backed by Redis.
- **Task Monitoring**: Web-based monitoring for Celery tasks via Flower.
- **Dockerized**: Easy setup with Docker Compose for API, Worker, Redis, and Postgres.
- **Standardized API Responses**: Consistent success and error shapes across all endpoints.

## Getting Started

### Prerequisites

- Docker and Docker Compose
- (Optional for local development) Python 3.12+ and `uv`

---

## 🐳 Running with Docker (Recommended)

The easiest way to run the entire stack is using Docker Compose.

1.  **Clone the repository.**
2.  **Create a `.env` file** (see `app/core/config.py` for required variables).
3.  **Start the services**:
    ```bash
    docker compose up --build
    ```

This will start:
- **API**: `http://localhost:8000`
- **Flower (Celery Monitor)**: `http://localhost:5555`
- **Postgres**: Port `5432`
- **Redis**: Port `6379`

---

## 🐍 Local Development

If you prefer to run the application locally (without Docker):

### Installation

1.  **Install dependencies**:
    ```bash
    uv sync
    ```
2.  **Ensure Redis is running** on `localhost:6379`.
3.  **Set up your `.env` file**.

### Running the Application

1.  **Start the Celery worker**:
    ```bash
    uv run celery -A app.queues.celery_task.app worker --loglevel=info
    ```
2.  **Start the FastAPI server**:
    ```bash
    uv run fastapi dev app/main.py
    ```
3.  **Start Flower**:
    ```bash
    uv run celery -A app.queues.celery_task.app flower
    ```

---

## 🤖 Running with Local LLMs (Ollama)

You can run DocuChat-Py entirely locally using Ollama.

1.  **Install Ollama**: Download from [ollama.com](https://ollama.com).
2.  **Pull Models**:
    ```bash
    ollama pull llama3.1
    ollama pull nomic-embed-text
    ```
3.  **Configure `.env`**:
    ```env
    OPENAI_API_KEY=ollama
    OPENAI_BASE_URL=http://localhost:11434/v1
    OPENAI_MODEL=llama3.1:latest
    OPENAI_EMBEDDING_MODEL=nomic-embed-text
    ```
    *Alternatively, you can copy the contents of the `_docker-compose-ollama.yml` file into `docker-compose.yml` and run the entire stack with Ollama.*

    *Note: If running the app inside **Docker**, use `http://host.docker.internal:11434/v1` as the base URL.*

---

## Testing & Linting

### Running Tests
```bash
uv run pytest
```

### Linting and Formatting
```bash
uv run ruff check .
uv run ruff format .
```

## Project Structure

- `app/`: Main application code.
  - `auth/`: Authentication logic and dependencies.
  - `core/`: Configuration, logging, and utilities.
  - `events/`: Event handlers.
  - `middleware/`: Custom middlewares.
  - `models/`: Database models and session management.
  - `queues/`: Celery task definitions.
  - `routers/`: API route definitions.
  - `schemas/`: Pydantic models for validation.
  - `services/`: External service integrations (OpenAI/Ollama).
- `migrations/`: Alembic database migrations.
- `scripts/`: Utility scripts (seeding, testing).
- `tests/`: Automated test suite.
