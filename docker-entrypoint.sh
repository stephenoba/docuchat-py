#!/bin/bash
set -e

# Run migrations
echo "Running alembic migrations..."
alembic upgrade head

# Run seed script if needed (Optional: You might want to guard this with an env var)
if [ "$SEED_DB" = "true" ]; then
    echo "Seeding database..."
    PYTHONPATH=. python scripts/seed_db.py
fi

# Execute the CMD from the Dockerfile (e.g., fastapi run)
echo "Starting application..."
exec "$@"
