web: celery -A tbc worker --loglevel=info & celery -A MeningitisPredictionProject beat --loglevel=info & python manage.py migrate && gunicorn MeningitisPredictionProject.wsgi --bind 0.0.0.0:$PORT
