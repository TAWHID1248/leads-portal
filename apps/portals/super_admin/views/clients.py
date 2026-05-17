from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Sum, Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.accounts.decorators import super_admin_required
from apps.agents.models import LeadAssignment
from apps.billing.models import Invoice, Order
from apps.clients.models import Client, Wallet, WalletTransaction
from apps.leads.models import LeadAllocation, ReplacementRequest
from apps.notifications.models import ActivityLog
from apps.notifications.services.email import send_client_welcome_email
from apps.portals.super_admin.forms import (
    ClientCreateForm,
    ClientUpdateForm,
    CreditWalletForm,
    generate_temp_password,
)

User = get_user_model()


def _annotate_clients(qs):
    return qs.select_related('user', 'wallet').annotate(
        leads_count=Count('allocations', distinct=True),
        active_subs=Count('subscriptions', filter=Q(subscriptions__status='ACTIVE'), distinct=True),
    )


@super_admin_required
def ClientListView(request):
    search = (request.GET.get('search') or '').strip()
    status = (request.GET.get('status') or '').strip()
    qs = _annotate_clients(Client.objects.all()).order_by('company_name')
    if search:
        qs = qs.filter(
            Q(company_name__icontains=search)
            | Q(user__email__icontains=search)
            | Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
        )
    if status:
        qs = qs.filter(user__status=status)
    return render(request, 'super_admin/clients/list.html', {
        'page_title': 'Clients',
        'clients': qs,
        'total_count': qs.count(),
        'search': search,
        'status': status,
        'statuses': User.Status.choices,
    })


@super_admin_required
def ClientCreateView(request):
    form = ClientCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        temp_password = data.get('password') or generate_temp_password()
        with transaction.atomic():
            user = User.objects.create_user(
                email=data['email'],
                password=temp_password,
                role=User.Role.CLIENT,
                status=User.Status.ACTIVE,
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                phone=data.get('phone', ''),
            )
            client = Client.objects.create(
                user=user,
                company_name=data['company_name'],
                country=data.get('country', '') or '',
                timezone=data.get('timezone') or 'UTC',
                billing_address=data.get('billing_address', '') or '',
                tax_id=data.get('tax_id', '') or '',
                webhook_url=data.get('webhook_url', '') or '',
                notify_email=data.get('notify_email', True),
                notify_sms=data.get('notify_sms', False),
            )
            Wallet.objects.create(client=client, balance=Decimal('0.00'))

        try:
            send_client_welcome_email(client, temp_password)
        except Exception as exc:
            messages.warning(request, f'Client created but welcome email failed: {exc}')

        ActivityLog.objects.create(
            user=request.user, action='client.created',
            entity_type='Client', entity_id=str(client.id),
            metadata={'email': user.email, 'company': client.company_name},
        )
        messages.success(request, f'Created client {client.company_name}.')
        return redirect('super_admin:client_detail', pk=client.id)

    return render(request, 'super_admin/clients/create.html', {
        'page_title': 'New client',
        'form': form,
    })


@super_admin_required
def ClientDetailView(request, pk):
    client = get_object_or_404(_annotate_clients(Client.objects.all()), pk=pk)
    wallet = getattr(client, 'wallet', None)
    return render(request, 'super_admin/clients/detail.html', {
        'page_title': client.company_name,
        'client': client,
        'wallet': wallet,
        'update_form': ClientUpdateForm(instance=client),
        'credit_form': CreditWalletForm(),
    })


@super_admin_required
def ClientUpdateView(request, pk):
    client = get_object_or_404(Client.objects.select_related('user'), pk=pk)
    form = ClientUpdateForm(request.POST or None, instance=client)
    if request.method == 'POST' and form.is_valid():
        form.save()
        ActivityLog.objects.create(
            user=request.user, action='client.updated',
            entity_type='Client', entity_id=str(client.id),
            metadata={'fields': list(form.changed_data)},
        )
        messages.success(request, 'Client updated.')
        return redirect('super_admin:client_detail', pk=client.id)
    return render(request, 'super_admin/clients/edit.html', {
        'page_title': f'Edit {client.company_name}',
        'client': client,
        'form': form,
    })


# ---------- HTMX tab partials ----------

@super_admin_required
def client_tab_overview(request, pk):
    client = get_object_or_404(_annotate_clients(Client.objects.all()), pk=pk)
    return render(request, 'super_admin/clients/_tab_overview.html', {
        'client': client,
        'wallet': getattr(client, 'wallet', None),
        'subscriptions': client.subscriptions.all().order_by('-id'),
    })


@super_admin_required
def client_tab_leads(request, pk):
    client = get_object_or_404(Client, pk=pk)
    allocations = (
        LeadAllocation.objects.filter(client=client)
        .select_related('lead')
        .order_by('-allocated_at')[:200]
    )
    return render(request, 'super_admin/clients/_tab_leads.html', {
        'client': client, 'allocations': allocations,
    })


@super_admin_required
def client_tab_orders(request, pk):
    client = get_object_or_404(Client, pk=pk)
    orders = Order.objects.filter(client=client).order_by('-id')
    return render(request, 'super_admin/clients/_tab_orders.html', {
        'client': client, 'orders': orders,
    })


@super_admin_required
def client_tab_invoices(request, pk):
    client = get_object_or_404(Client, pk=pk)
    invoices = Invoice.objects.filter(client=client).order_by('-id')
    return render(request, 'super_admin/clients/_tab_invoices.html', {
        'client': client, 'invoices': invoices,
    })


@super_admin_required
def client_tab_replacements(request, pk):
    client = get_object_or_404(Client, pk=pk)
    items = (
        ReplacementRequest.objects.filter(client=client)
        .select_related('lead', 'replacement_lead')
        .order_by('-id')
    )
    return render(request, 'super_admin/clients/_tab_replacements.html', {
        'client': client, 'items': items,
    })


@super_admin_required
def client_tab_activity(request, pk):
    client = get_object_or_404(Client, pk=pk)
    activity = (
        ActivityLog.objects
        .filter(entity_type='Client', entity_id=str(client.id))
        .order_by('-created_at')[:100]
    )
    return render(request, 'super_admin/clients/_tab_activity.html', {
        'client': client, 'activity': activity,
    })


# ---------- Actions ----------

@super_admin_required
@require_POST
def credit_wallet_view(request, pk):
    client = get_object_or_404(Client, pk=pk)
    form = CreditWalletForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest('Invalid amount')

    amount = form.cleaned_data['amount']
    note = form.cleaned_data.get('note') or 'Manual credit'

    with transaction.atomic():
        wallet, _ = Wallet.objects.get_or_create(client=client)
        wallet.balance = (wallet.balance or Decimal('0.00')) + amount
        wallet.save(update_fields=['balance'])
        WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            tx_type=WalletTransaction.TxType.CREDIT_ADJUSTMENT,
            description=note,
            reference=f'admin:{request.user.id}',
            balance_after=wallet.balance,
        )

    ActivityLog.objects.create(
        user=request.user, action='client.wallet_credited',
        entity_type='Client', entity_id=str(client.id),
        metadata={'amount': str(amount), 'note': note},
    )
    messages.success(request, f'Credited ${amount} to {client.company_name}.')
    return redirect('super_admin:client_detail', pk=client.id)


@super_admin_required
@require_POST
def suspend_client_view(request, pk):
    client = get_object_or_404(Client.objects.select_related('user'), pk=pk)
    new_status = request.POST.get('status') or User.Status.SUSPENDED
    if new_status not in dict(User.Status.choices):
        return HttpResponseBadRequest('Invalid status')
    client.user.status = new_status
    client.user.save(update_fields=['status'])
    ActivityLog.objects.create(
        user=request.user, action='client.status_changed',
        entity_type='Client', entity_id=str(client.id),
        metadata={'new_status': new_status},
    )
    messages.success(request, f'{client.company_name} is now {new_status}.')
    return redirect('super_admin:client_detail', pk=client.id)
