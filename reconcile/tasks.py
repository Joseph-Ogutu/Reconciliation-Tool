from celery import shared_task
from .models import Reconciliation
from .views import process_reconciliation
import pandas as pd
from datetime import datetime

@shared_task
def run_reconciliation(reconciliation_id: int):
    try:
        reconciliation = Reconciliation.objects.get(id=reconciliation_id)
        internal_df = pd.read_csv(reconciliation.internal_file.path)
        provider_df = pd.read_csv(reconciliation.provider_file.path)

        true_matches, mismatched_matches, internal_only, provider_only = process_reconciliation(internal_df, provider_df)

        reconciliation.last_reconciled = datetime.now()
        reconciliation.save()
    except Exception as e:
        print(f"Error running reconciliation: {str(e)}")

@shared_task
def schedule_reconciliations():
    try:
        for reconciliation in Reconciliation.objects.filter(schedule_frequency__in=['daily', 'weekly']):
            if reconciliation.schedule_frequency == 'daily' or (reconciliation.schedule_frequency == 'weekly' and datetime.now().weekday() == 0):
                run_reconciliation.delay(reconciliation.id)
    except Exception as e:
        print(f"Error scheduling reconciliations: {str(e)}")