from django.urls import path

from apps.portals.admin_portal import views

app_name = 'admin_portal'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/chart-data/', views.dashboard_chart_data, name='dashboard_chart_data'),

    path('leads/', views.leads_list, name='leads_list'),
    path('leads/export/', views.leads_export_view, name='leads_export'),
    path('leads/<int:pk>/update/', views.lead_update_view, name='lead_update'),

    path('replacements/', views.replacements_view, name='replacements'),
    path('replacements/<int:pk>/approve/', views.approve_replacement_view, name='replacement_approve'),
    path('replacements/<int:pk>/deny/', views.deny_replacement_view, name='replacement_deny'),

    path('reports/leads/', views.leads_report_view, name='report_leads'),
    path('reports/revenue/', views.revenue_report_view, name='report_revenue'),
]
