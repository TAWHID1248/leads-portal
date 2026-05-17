from django.urls import path

from apps.portals.agent import views

app_name = 'agent'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/chart-data/', views.chart_data_view, name='chart_data'),

    path('leads/', views.LeadListView, name='leads_list'),
    path('leads/<int:pk>/drawer/', views.lead_drawer_view, name='lead_drawer'),
    path('leads/<int:pk>/log-call/', views.log_call_view, name='log_call'),

    path('calls/', views.calls_view, name='calls'),
    path('calls/export/', views.calls_export_view, name='calls_export'),

    path('targets/', views.targets_view, name='targets'),
]
