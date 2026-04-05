#!/bin/bash

# Exit on error
set -e

# Wait for PgBouncer to be ready
echo "Waiting for database..."
while ! nc -z pgbouncer 6432; do
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
