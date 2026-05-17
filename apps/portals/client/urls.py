from django.urls import path

from apps.portals.client import views

app_name = 'client'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/chart-data/', views.chart_data_view, name='chart_data'),

    # Leads
    path('leads/', views.LeadListView, name='leads_list'),
    path('leads/export/', views.export_view, name='leads_export'),
    path('leads/<int:pk>/drawer/', views.LeadDetailDrawerView, name='lead_drawer'),
    path('leads/<int:pk>/status/', views.update_status_view, name='lead_update_status'),
    path('leads/<int:pk>/replace/', views.request_replacement_view, name='lead_replace'),

    # Wallet
    path('wallet/', views.wallet_view, name='wallet'),
    path('wallet/topup-intent/', views.topup_intent_view, name='wallet_topup_intent'),

    # Pricing / Buy
    path('pricing/', views.pricing_view, name='pricing'),
    path('pricing/buy/', views.buy_leads_view, name='buy_leads'),

    # Orders
    path('orders/', views.orders_view, name='orders'),

    # Subscriptions
    path('subscriptions/', views.subscriptions_view, name='subscriptions'),
    path('subscriptions/new/', views.create_subscription_view, name='subscriptions_create'),
    path('subscriptions/<int:pk>/cancel/', views.cancel_subscription_view, name='subscriptions_cancel'),

    # Invoices
    path('invoices/', views.invoices_view, name='invoices'),
    path('invoices/<int:pk>/pdf/', views.invoice_pdf_view, name='invoice_pdf'),

    # Replacements
    path('replacements/', views.replacements_view, name='replacements'),
    path('replacements/eligible/', views.eligible_leads_view, name='replacements_eligible'),
    path('replacements/new/', views.submit_replacement_view, name='replacements_submit'),
]
