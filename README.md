Reconciliation Tool

A Django-based web application for comparing transaction data between an internal system export and a payment processor's statement, identifying discrepancies, and visualizing results with an interactive dashboard.

## Features
- **File Upload**: Upload two CSV files (Internal System Export and Provider Statement).
- **Reconciliation**: Compare transactions using `transaction_reference`, with advanced matching on `amount`, `status`, `currency`, and `customer_id`.
- **Discrepancy Categorization**: Displays results in four categories:
  - True Matches: Transactions matching all fields.
  - Mismatched Matches: Transactions with discrepancies in amount, status, currency, or customer_id.
  - Internal Only: Transactions only in the internal file.
  - Provider Only: Transactions only in the provider file.
- **Time-Based Analysis**: Filter transactions by date range.
- **Interactive Filters**: Dynamically filter results by transaction reference using JavaScript.
- **Visualization**: Bar chart of transaction counts using Chart.js.
- **Export Options**: Export each category as CSV and download a PDF report.
- **Automation**: Schedule periodic reconciliations (daily/weekly) using Celery.

## Prerequisites
- Python 3.8+
- Django 5.0+
- Redis (for Celery)
- Dependencies: `django`, `pandas`, `numpy`, `django-pandas`, `celery`, `redis`, `reportlab`

## Installation
1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd reconciliation_tool
