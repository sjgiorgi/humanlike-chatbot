#!/bin/sh

host="$DATABASE_HOST"
user="$DATABASE_USER"
password="$DATABASE_PASSWORD"

echo "Waiting for MySQL to be ready..."
until mysql -h "$host" -u "$user" -p"$password" -e 'SELECT 1' > /dev/null 2>&1; do
  >&2 echo "MySQL is unavailable - sleeping"
  sleep 1
done

>&2 echo "✅ MySQL is up - proceeding with migrations"

# Run Django migrations
echo "Running makemigrations..."

python manage.py makemigrations --noinput
if [ $? -eq 0 ]; then
    echo "✅ Makemigrations completed successfully."
else
    echo "❌ Error running makemigrations."
    exit 1
fi

echo "Running migrate..."
python manage.py migrate --noinput
if [ $? -eq 0 ]; then
    echo "✅ Migrations applied successfully."
else
    echo "❌ Error applying migrations."
    exit 1
fi

# Collect static files (to match production behavior)
echo "Collecting static files..."
python manage.py collectstatic --noinput
if [ $? -eq 0 ]; then
    echo "✅ Static files collected successfully."
else
    echo "❌ Error collecting static files."
    exit 1
fi

# Load bots if necessary
echo "Loading bots..."
python manage.py load_bots
if [ $? -eq 0 ]; then
    echo "✅ Bots loaded successfully."
else
    echo "❌ Error loading bots."
    exit 1
fi

>&2 echo "✅ All setup tasks completed. Starting application..."


# Execute the original command (e.g., runserver)
exec "$@"
