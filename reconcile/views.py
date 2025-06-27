import pandas as pd
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from .models import Reconciliation
from .forms import ReconciliationForm, DateFilterForm
from django.contrib.auth.forms import AuthenticationForm
import json
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from typing import Tuple, Dict
from django.contrib.auth import authenticate, login
import logging

# Set up logging
logger = logging.getLogger(__name__)

def validate_file(file):
    # Check if file is a CSV
    if not file.name.endswith('.csv'):
        raise ValueError("Invalid file type. Only CSV files are allowed.")

    # Check if file is not empty
    if file.size == 0:
        raise ValueError("File is empty.")

def process_reconciliation(internal_df: pd.DataFrame, provider_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    try:
        # Validate dataframes
        required_columns = ['transaction_reference', 'amount', 'status', 'date', 'currency', 'customer_id']
        if not all(col in internal_df.columns for col in required_columns):
            raise ValueError("Internal file is missing required columns.")
        if not all(col in provider_df.columns for col in required_columns):
            raise ValueError("Provider file is missing required columns.")

        # Convert transaction_reference and other fields to string
        for col in ['transaction_reference', 'currency', 'customer_id']:
            internal_df[col] = internal_df[col].astype(str)
            provider_df[col] = provider_df[col].astype(str)

        # Merge and categorize transactions
        merged = internal_df.merge(provider_df, on='transaction_reference', how='outer', suffixes=('_internal', '_provider'), indicator=True)
        matches = merged[merged['_merge'] == 'both'].copy()
        internal_only = merged[merged['_merge'] == 'left_only']
        provider_only = merged[merged['_merge'] == 'right_only']

        # Check for mismatches in amount, status, currency, and customer_id
        matches['amount_mismatch'] = matches.apply(
            lambda row: row['amount_internal'] != row['amount_provider'] if 'amount_internal' in row and 'amount_provider' in row else False, axis=1
        )
        matches['status_mismatch'] = matches.apply(
            lambda row: row['status_internal'] != row['status_provider'] if 'status_internal' in row and 'status_provider' in row else False, axis=1
        )
        matches['currency_mismatch'] = matches.apply(
            lambda row: row['currency_internal'] != row['currency_provider'] if 'currency_internal' in row and 'currency_provider' in row else False, axis=1
        )
        matches['customer_id_mismatch'] = matches.apply(
            lambda row: row['customer_id_internal'] != row['customer_id_provider'] if 'customer_id_internal' in row and 'customer_id_provider' in row else False, axis=1
        )

        # Filter true matches
        true_matches = matches[
            (matches['amount_mismatch'] == False) &
            (matches['status_mismatch'] == False) &
            (matches['currency_mismatch'] == False) &
            (matches['customer_id_mismatch'] == False)
        ]
        mismatched_matches = matches[
            (matches['amount_mismatch'] == True) |
            (matches['status_mismatch'] == True) |
            (matches['currency_mismatch'] == True) |
            (matches['customer_id_mismatch'] == True)
        ]

        return true_matches, mismatched_matches, internal_only, provider_only
    except Exception as e:
        logger.error(f"Error processing reconciliation: {str(e)}")
        raise ValueError(f"Error processing reconciliation: {str(e)}")

def generate_pdf(true_matches: pd.DataFrame, mismatched_matches: pd.DataFrame, internal_only: pd.DataFrame, provider_only: pd.DataFrame) -> bytes:
    try:
        response = HttpResponse(content_type='application/pdf')
        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("Reconciliation Report", styles['Title']))
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))

        def create_table(df: pd.DataFrame, title: str):
            elements.append(Paragraph(title, styles['Heading2']))
            if not df.empty:
                data = [df.columns.tolist()] + df.values.tolist()
                table = Table(data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(table)
            else:
                elements.append(Paragraph("No data available.", styles['Normal']))

        create_table(true_matches, "True Matches")
        create_table(mismatched_matches, "Mismatched Matches")
        create_table(internal_only, "Internal Only")
        create_table(provider_only, "Provider Only")

        doc.build(elements)
        return response
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        raise ValueError(f"Error generating PDF: {str(e)}")

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

@login_required
def upload_files(request):
    if request.method == 'POST':
        form = ReconciliationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Validate files
                validate_file(request.FILES['internal_file'])
                validate_file(request.FILES['provider_file'])

                reconciliation = form.save(commit=False)
                reconciliation.user = request.user
                reconciliation.save()
                return redirect('reconciliation_results', reconciliation_id=reconciliation.id)
            except Exception as e:
                logger.error(f"Error uploading files: {str(e)}")
                return render(request, 'upload.html', {'form': form, 'error': str(e)})
    else:
        form = ReconciliationForm()
    return render(request, 'upload.html', {'form': form})

@login_required
def reconciliation_results(request, reconciliation_id: int):
    try:
        reconciliation = Reconciliation.objects.get(id=reconciliation_id, user=request.user)
        filter_form = DateFilterForm(request.GET)
        internal_df = pd.read_csv(reconciliation.internal_file.path)
        provider_df = pd.read_csv(reconciliation.provider_file.path)

        # Validate dataframes
        required_columns = ['transaction_reference', 'amount', 'status', 'date', 'currency', 'customer_id']
        if not all(col in internal_df.columns for col in required_columns):
            raise ValueError("Internal file is missing required columns.")
        if not all(col in provider_df.columns for col in required_columns):
            raise ValueError("Provider file is missing required columns.")

        if filter_form.is_valid() and filter_form.cleaned_data['start_date'] and filter_form.cleaned_data['end_date']:
            start_date = filter_form.cleaned_data['start_date']
            end_date = filter_form.cleaned_data['end_date']
            internal_df['date'] = pd.to_datetime(internal_df['date'])
            internal_df = internal_df[(internal_df['date'] >= start_date) & (internal_df['date'] <= end_date)]
            provider_df['date'] = pd.to_datetime(provider_df['date'])
            provider_df = provider_df[(provider_df['date'] >= start_date) & (provider_df['date'] <= end_date)]

        true_matches, mismatched_matches, internal_only, provider_only = process_reconciliation(internal_df, provider_df)

        chart_data = {
            'labels': ['True Matches', 'Mismatched Matches', 'Internal Only', 'Provider Only'],
            'counts': [int(len(true_matches)), int(len(mismatched_matches)), int(len(internal_only)), int(len(provider_only))],
        }

        context = {
            'reconciliation': reconciliation,
            'true_matches': true_matches.to_dict('records'),
            'mismatched_matches': mismatched_matches.to_dict('records'),
            'internal_only': internal_only.to_dict('records'),
            'provider_only': provider_only.to_dict('records'),
            'chart_data': json.dumps(chart_data),
            'filter_form': filter_form,
            'reconciliation_id': reconciliation_id,
        }
        return render(request, 'results.html', context)
    except Exception as e:
        logger.error(f"Error getting reconciliation results: {str(e)}")
        return render(request, 'results.html', {'error': str(e)})

@login_required
def export_category(request, reconciliation_id: int, category: str):
    try:
        reconciliation = Reconciliation.objects.get(id=reconciliation_id, user=request.user)
        internal_df = pd.read_csv(reconciliation.internal_file.path)
        provider_df = pd.read_csv(reconciliation.provider_file.path)

        true_matches, mismatched_matches, internal_only, provider_only = process_reconciliation(internal_df, provider_df)

        if category == 'true_matches':
            df = true_matches
        elif category == 'mismatched_matches':
            df = mismatched_matches
        elif category == 'internal_only':
            df = internal_only
        elif category == 'provider_only':
            df = provider_only
        else:
            return HttpResponse("Invalid category", status=400)

        response = HttpResponse(content_type='text/csv', headers={'Content-Disposition': f'attachment; filename="{category}.csv"'})
        df.to_csv(response, index=False)
        return response
    except Exception as e:
        logger.error(f"Error exporting category: {str(e)}")
        return HttpResponse(str(e), status=500)

@login_required
def download_pdf(request, reconciliation_id: int):
    try:
        reconciliation = Reconciliation.objects.get(id=reconciliation_id, user=request.user)
        internal_df = pd.read_csv(reconciliation.internal_file.path)
        provider_df = pd.read_csv(reconciliation.provider_file.path)

        true_matches, mismatched_matches, internal_only, provider_only = process_reconciliation(internal_df, provider_df)

        response = generate_pdf(true_matches, mismatched_matches, internal_only, provider_only)
        response['Content-Disposition'] = f'attachment; filename="reconciliation_{reconciliation_id}.pdf"'
        return response
    except Exception as e:
        logger.error(f"Error downloading PDF: {str(e)}")
        return HttpResponse(str(e), status=500)