#!/bin/sh

# Start Gunicorn
gunicorn MeningitisPredictionProject.wsgi:application --bind 0.0.0.0:${PORT:-8000} &

# Start Celery worker
celery -A MeningitisPredictionProject worker --loglevel=info &

# Start Celery beat
celery -A MeningitisPredictionProject beat --loglevel=info
