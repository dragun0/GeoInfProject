web: gunicorn MeningitisPredictionProject.wsgi --log-file -
worker: celery -A MeningitisPredictionProject worker --loglevel=info
beat: celery -A MeningitisPredictionProject beat --loglevel=info
