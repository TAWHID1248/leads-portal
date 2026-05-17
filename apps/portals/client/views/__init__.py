from apps.portals.client.views.dashboard import dashboard, chart_data_view
from apps.portals.client.views.leads import (
    LeadListView,
    LeadDetailDrawerView,
    update_status_view,
    export_view,
    request_replacement_view,
)
from apps.portals.client.views.wallet import wallet_view, topup_intent_view
from apps.portals.client.views.pricing import pricing_view, buy_leads_view
from apps.portals.client.views.orders import orders_view
from apps.portals.client.views.subscriptions import (
    subscriptions_view,
    create_subscription_view,
    cancel_subscription_view,
)
from apps.portals.client.views.invoices import invoices_view, invoice_pdf_view
from apps.portals.client.views.replacements import (
    replacements_view,
    eligible_leads_view,
    submit_replacement_view,
)

__all__ = [
    'dashboard', 'chart_data_view',
    'LeadListView', 'LeadDetailDrawerView', 'update_status_view', 'export_view',
    'request_replacement_view',
    'wallet_view', 'topup_intent_view',
    'pricing_view', 'buy_leads_view',
    'orders_view',
    'subscriptions_view', 'create_subscription_view', 'cancel_subscription_view',
    'invoices_view', 'invoice_pdf_view',
    'replacements_view', 'eligible_leads_view', 'submit_replacement_view',
]
