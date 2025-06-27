
from django import forms
from .models import Reconciliation

class ReconciliationForm(forms.ModelForm):
    schedule_frequency = forms.ChoiceField(choices=[('', 'None'), ('daily', 'Daily'), ('weekly', 'Weekly')], required=False)
    
    class Meta:
        model = Reconciliation
        fields = ['internal_file', 'provider_file', 'schedule_frequency']

class DateFilterForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)