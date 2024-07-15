web: python manage.py migrate && gunicorn MeningitisPredictionProject.wsgi
worker: celery -A MeningitisPredictionProject worker --loglevel=info
beat: celery -A MeningitisPredictionProject beat --loglevel=info
