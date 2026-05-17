from django.urls import path

from apps.leads.api.views import LeadIngestView

app_name = 'leads_api'

urlpatterns = [
    path('leads/ingest', LeadIngestView.as_view(), name='lead_ingest'),
]
