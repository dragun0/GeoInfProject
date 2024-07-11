from celery import shared_task
from django.core.management import call_command

@shared_task
def generate_risk_map():
    call_command('generate_risk_map')