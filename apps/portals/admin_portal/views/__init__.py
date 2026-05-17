from apps.portals.admin_portal.views.dashboard import dashboard, dashboard_chart_data
from apps.portals.admin_portal.views.replacements import (
    replacements_view,
    approve_replacement_view,
    deny_replacement_view,
)
from apps.portals.admin_portal.views.leads import (
    leads_list, lead_update_view, leads_export_view,
)
from apps.portals.admin_portal.views.reports import (
    leads_report_view, revenue_report_view,
)

__all__ = [
    'dashboard', 'dashboard_chart_data',
    'replacements_view', 'approve_replacement_view', 'deny_replacement_view',
    'leads_list', 'lead_update_view', 'leads_export_view',
    'leads_report_view', 'revenue_report_view',
]
