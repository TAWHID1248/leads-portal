from django.urls import path

from apps.portals.super_admin import views
from apps.portals.super_admin.views import (
    leads as leads_views,
    clients as clients_views,
    agents as agents_views,
    settings as settings_views,
    replacements as replacements_views,
    sweepstakes as sweepstakes_views,
    users as users_views,
    billing as billing_views,
)

app_name = 'super_admin'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/chart-data/', views.dashboard_chart_data, name='dashboard_chart_data'),

    # Users
    path('users/', users_views.users_list, name='users_list'),

    # Billing
    path('billing/', billing_views.billing_overview, name='billing'),

    # Leads
    path('leads/', leads_views.LeadListView, name='leads_list'),
    path('leads/bulk-assign/', leads_views.bulk_assign_view, name='leads_bulk_assign'),
    path('leads/bulk-export/', leads_views.bulk_export_view, name='leads_bulk_export'),
    path('leads/bulk-reject/', leads_views.bulk_reject_view, name='leads_bulk_reject'),
    path('leads/<int:pk>/', leads_views.LeadDetailView, name='lead_detail'),
    path('leads/<int:pk>/drawer/', leads_views.lead_drawer_view, name='lead_drawer'),
    path('leads/<int:pk>/assign/', leads_views.assign_lead_view, name='lead_assign'),
    path('leads/<int:pk>/update/', leads_views.update_lead_view, name='lead_update'),

    # Clients
    path('clients/', clients_views.ClientListView, name='client_list'),
    path('clients/new/', clients_views.ClientCreateView, name='client_create'),
    path('clients/<int:pk>/', clients_views.ClientDetailView, name='client_detail'),
    path('clients/<int:pk>/edit/', clients_views.ClientUpdateView, name='client_edit'),
    path('clients/<int:pk>/credit/', clients_views.credit_wallet_view, name='client_credit'),
    path('clients/<int:pk>/suspend/', clients_views.suspend_client_view, name='client_suspend'),
    path('clients/<int:pk>/tabs/overview/',     clients_views.client_tab_overview,     name='client_tab_overview'),
    path('clients/<int:pk>/tabs/leads/',        clients_views.client_tab_leads,        name='client_tab_leads'),
    path('clients/<int:pk>/tabs/orders/',       clients_views.client_tab_orders,       name='client_tab_orders'),
    path('clients/<int:pk>/tabs/invoices/',     clients_views.client_tab_invoices,     name='client_tab_invoices'),
    path('clients/<int:pk>/tabs/replacements/', clients_views.client_tab_replacements, name='client_tab_replacements'),
    path('clients/<int:pk>/tabs/activity/',     clients_views.client_tab_activity,     name='client_tab_activity'),

    # Agents
    path('agents/', agents_views.AgentListView, name='agent_list'),
    path('agents/new/', agents_views.AgentCreateView, name='agent_create'),
    path('agents/<int:pk>/', agents_views.AgentDetailView, name='agent_detail'),
    path('agents/<int:pk>/stats/', agents_views.get_agent_stats, name='agent_stats'),

    # Settings
    path('settings/', settings_views.settings_view, name='settings'),
    path('settings/update/', settings_views.update_setting_view, name='settings_update'),
    path('settings/ingest-key/regenerate/', settings_views.regenerate_ingest_key_view, name='settings_regenerate_ingest_key'),

    # Replacements
    path('replacements/', replacements_views.replacements_view, name='replacements'),
    path('replacements/<int:pk>/approve/', replacements_views.approve_replacement_view, name='replacement_approve'),
    path('replacements/<int:pk>/deny/', replacements_views.deny_replacement_view, name='replacement_deny'),

    # Facebook Groups
    path('facebook-groups/', views.facebook_groups_list, name='facebook_groups'),
    path('facebook-groups/new/', views.facebook_group_create, name='facebook_group_create'),
    path('facebook-groups/<int:pk>/edit/', views.facebook_group_edit, name='facebook_group_edit'),
    path('facebook-groups/<int:pk>/delete/', views.facebook_group_delete, name='facebook_group_delete'),

    # Sweepstakes
    path('sweepstakes/', sweepstakes_views.SweepstakesListView, name='sweepstakes_list'),
    path('sweepstakes/new/', sweepstakes_views.SweepstakesCreateView, name='sweepstakes_create'),
    path('sweepstakes/<int:pk>/', sweepstakes_views.SweepstakesDetailView, name='sweepstakes_detail'),
    path('sweepstakes/<int:pk>/edit/', sweepstakes_views.SweepstakesUpdateView, name='sweepstakes_edit'),
    path('sweepstakes/<int:pk>/draw/', sweepstakes_views.draw_winner_view, name='sweepstakes_draw'),
    path('sweepstakes/<int:pk>/notify-winner/', sweepstakes_views.notify_winner_view, name='sweepstakes_notify'),
]
