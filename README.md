# tnzak

## Локальный запуск

1. Установить зависимости:
   pip install -r requirements.txt
2. Применить миграции:
   python manage.py migrate
3. Запустить сервер:
   python manage.py runserver

## Railway

1. Подключить репозиторий в Railway.
2. Добавить PostgreSQL через Add Service -> Database -> PostgreSQL.
3. Убедиться, что в Variables есть:
   - SECRET_KEY
   - DEBUG=False
   - ALLOWED_HOSTS=.railway.app
   - CSRF_TRUSTED_ORIGINS=https://<your-domain>.railway.app
   - DATABASE_URL (обычно создается автоматически после подключения PostgreSQL)
4. Railway запустит приложение через команду из railway.json / Procfile.

При старте контейнера выполняются:
- python manage.py migrate --noinput
- python manage.py collectstatic --noinput
- gunicorn tnzak.wsgi:application --bind 0.0.0.0:$PORT
