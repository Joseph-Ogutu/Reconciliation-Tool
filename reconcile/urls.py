from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/', views.upload_files, name='upload_files'),
    path('results/<int:reconciliation_id>/', views.reconciliation_results, name='reconciliation_results'),
    path('export/<int:reconciliation_id>/<str:category>/', views.export_category, name='export_category'),
    path('pdf/<int:reconciliation_id>/', views.download_pdf, name='download_pdf'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]