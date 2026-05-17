from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.accounts.decorators import super_admin_required
from apps.agents.models import Agent, CallLog, LeadAssignment
from apps.notifications.models import ActivityLog
from apps.notifications.services.email import send_agent_welcome_email
from apps.portals.super_admin.forms import (
    AgentCreateForm,
    AgentUpdateForm,
    generate_temp_password,
)

User = get_user_model()


def _stats_for_agents(qs):
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)
    return qs.annotate(
        leads_assigned=Count('assignments', distinct=True),
        calls_today=Count('call_logs', filter=Q(call_logs__called_at__gte=today_start), distinct=True),
        sold_this_week=Count('assignments', filter=Q(assignments__status='SOLD',
                                                      assignments__assigned_at__gte=week_start),
                              distinct=True),
        commission_month=Sum('assignments__lead__sold_price',
                             filter=Q(assignments__status='SOLD',
                                      assignments__assigned_at__gte=month_start)),
    )


@super_admin_required
def AgentListView(request):
    qs = _stats_for_agents(Agent.objects.select_related('user')).order_by('user__email')
    return render(request, 'super_admin/agents/list.html', {
        'page_title': 'Agents',
        'agents': qs,
        'total_count': qs.count(),
    })


@super_admin_required
def AgentCreateView(request):
    form = AgentCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        temp_password = data.get('password') or generate_temp_password()
        with transaction.atomic():
            user = User.objects.create_user(
                email=data['email'],
                password=temp_password,
                role=User.Role.AGENT,
                status=User.Status.ACTIVE,
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                phone=data.get('phone', ''),
            )
            agent = Agent.objects.create(
                user=user,
                target_leads=data['target_leads'],
                target_revenue=data['target_revenue'],
                commission=data['commission'],
            )

        try:
            send_agent_welcome_email(agent, temp_password)
        except Exception as exc:
            messages.warning(request, f'Agent created but welcome email failed: {exc}')

        ActivityLog.objects.create(
            user=request.user, action='agent.created',
            entity_type='Agent', entity_id=str(agent.id),
            metadata={'email': user.email},
        )
        messages.success(request, f'Created agent {user.email}.')
        return redirect('super_admin:agent_detail', pk=agent.id)

    return render(request, 'super_admin/agents/create.html', {
        'page_title': 'New agent',
        'form': form,
    })


@super_admin_required
def AgentDetailView(request, pk):
    agent = get_object_or_404(_stats_for_agents(Agent.objects.select_related('user')), pk=pk)
    form = AgentUpdateForm(request.POST or None, instance=agent)
    if request.method == 'POST' and form.is_valid():
        form.save()
        ActivityLog.objects.create(
            user=request.user, action='agent.updated',
            entity_type='Agent', entity_id=str(agent.id),
            metadata={'fields': list(form.changed_data)},
        )
        messages.success(request, 'Agent updated.')
        return redirect('super_admin:agent_detail', pk=agent.id)
    recent_assignments = LeadAssignment.objects.filter(agent=agent).select_related('lead').order_by('-id')[:25]
    recent_calls = CallLog.objects.filter(agent=agent).order_by('-called_at')[:25]
    return render(request, 'super_admin/agents/detail.html', {
        'page_title': agent.user.get_full_name() or agent.user.email,
        'agent': agent,
        'form': form,
        'recent_assignments': recent_assignments,
        'recent_calls': recent_calls,
    })


@super_admin_required
@require_GET
def get_agent_stats(request, pk):
    agent = get_object_or_404(_stats_for_agents(Agent.objects.select_related('user')), pk=pk)
    return render(request, 'super_admin/agents/_stats.html', {'agent': agent})
