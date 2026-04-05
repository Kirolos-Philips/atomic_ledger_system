#!/bin/bash

# Exit on error
set -e

# Wait for database (PgBouncer in prod, directly in dev)
echo "Waiting for database at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
while ! nc -z ${POSTGRES_HOST} ${POSTGRES_PORT}; do
  sleep 0.5
done
echo "Database is ready!"

# Apply database migrations
echo "Applying database migrations..."
uv run python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
uv run python manage.py collectstatic --noinput

# Start the application
echo "Starting server..."
exec "$@"
