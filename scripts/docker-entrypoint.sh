#!/usr/bin/env bash
set -e

echo "=== RoadAthena AI Container Starting ==="

wait_for_tcp() {
  local host="$1"
  local port="$2"
  local name="$3"
  echo "Checking TCP connectivity for $name ($host:$port)..."
  for i in {1..60}; do
    if (echo > /dev/tcp/"$host"/"$port") 2>/dev/null || nc -z "$host" "$port" 2>/dev/null; then
      echo "$name is ready!"
      return 0
    fi
    sleep 0.5
  done
  echo "ERROR: Timed out waiting for $name at $host:$port"
  return 1
}

# Wait for PostgreSQL if configured
if [[ "$DATABASE_URL" == *"postgres"* ]]; then
  DB_HOST="${DB_HOST:-db}"
  DB_PORT="${DB_PORT:-5432}"
  wait_for_tcp "$DB_HOST" "$DB_PORT" "PostgreSQL Database"
fi

# Wait for Redis if configured
if [[ "$CELERY_BROKER_URL" == *"redis"* ]] || [[ "$REDIS_URL" == *"redis"* ]]; then
  REDIS_HOST="${REDIS_HOST:-redis}"
  REDIS_PORT="${REDIS_PORT:-6379}"
  wait_for_tcp "$REDIS_HOST" "$REDIS_PORT" "Redis Message Broker"
fi

# Run Django migrations and static assets collection on web service start
if [[ "$1" == "gunicorn"* ]] || [[ "$1" == "python" && "$2" == "manage.py" && "$3" == "runserver"* ]]; then
  echo "Applying database schema migrations..."
  python manage.py migrate --noinput

  echo "Collecting static assets..."
  python manage.py collectstatic --noinput || true
fi

# For Celery worker, add a 5-second grace delay to allow migrations to complete
if [[ "$1" == "celery"* ]]; then
  echo "Worker waiting 5s for web migrations grace period..."
  sleep 5
fi

echo "Executing container command: $@"
exec "$@"
