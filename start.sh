#!/usr/bin/env bash
set -e

python manage.py migrate --noinput
python manage.py init_test_data
python manage.py collectstatic --noinput
gunicorn tnzak.wsgi:application --bind 0.0.0.0:${PORT:-8000}
