#!/bin/sh

# Start Gunicorn
python manage.py runserver 0.0.0.0:8080 &

# Start Celery worker
celery -A MeningitisPredictionProject worker --loglevel=info &

# Start Celery beat
celery -A MeningitisPredictionProject beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler