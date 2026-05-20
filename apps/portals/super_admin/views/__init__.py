from apps.portals.super_admin.views.dashboard import dashboard, dashboard_chart_data
from apps.portals.super_admin.views.leads import (
    LeadListView,
    LeadDetailView,
    lead_drawer_view,
    assign_lead_view,
    update_lead_view,
    bulk_assign_view,
    bulk_export_view,
    bulk_reject_view,
    niche_leads_view,
)
from apps.portals.super_admin.views.clients import (
    ClientListView,
    ClientCreateView,
    ClientDetailView,
    ClientUpdateView,
    credit_wallet_view,
    suspend_client_view,
    client_tab_overview,
    client_tab_leads,
    client_tab_orders,
    client_tab_invoices,
    client_tab_replacements,
    client_tab_activity,
)
from apps.portals.super_admin.views.agents import (
    AgentListView,
    AgentCreateView,
    AgentDetailView,
    get_agent_stats,
)
from apps.portals.super_admin.views.settings import (
    settings_view,
    update_setting_view,
    regenerate_ingest_key_view,
)
from apps.portals.super_admin.views.replacements import (
    replacements_view as super_replacements_view,
    approve_replacement_view as super_approve_replacement_view,
    deny_replacement_view as super_deny_replacement_view,
)
from apps.portals.super_admin.views.users import users_list
from apps.portals.super_admin.views.billing import billing_overview
leads_list = LeadListView  # back-compat
