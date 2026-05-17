web: gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 3 --access-logfile - --error-logfile -
worker: celery -A config worker -l info
beat: celery -A config beat -l info
release: python manage.py migrate --noinput
