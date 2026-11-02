from django.urls import path

from . import views

urlpatterns = [
    path('health/', views.health_view, name='health'),
    path('investigations/', views.InvestigationListView.as_view(), name='investigation-list'),
    path('investigations/<uuid:pk>/', views.InvestigationDetailView.as_view(), name='investigation-detail'),
    path('investigations/<uuid:pk>/upload/', views.InvestigationUploadView.as_view(), name='investigation-upload'),
    path('investigations/<uuid:pk>/events/', views.InvestigationEventsView.as_view(), name='investigation-events'),
    path('investigations/<uuid:pk>/correlations/', views.InvestigationCorrelationsView.as_view(), name='investigation-correlations'),
    path('investigations/<uuid:pk>/export/', views.export_investigation, name='investigation-export'),
]
