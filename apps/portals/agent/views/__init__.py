from apps.portals.agent.views.dashboard import dashboard, chart_data_view
from apps.portals.agent.views.leads import (
    LeadListView,
    lead_drawer_view,
    log_call_view,
)
from apps.portals.agent.views.calls import calls_view, calls_export_view
from apps.portals.agent.views.targets import targets_view

__all__ = [
    'dashboard', 'chart_data_view',
    'LeadListView', 'lead_drawer_view', 'log_call_view',
    'calls_view', 'calls_export_view',
    'targets_view',
]
