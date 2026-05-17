from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from apps.accounts.decorators import super_admin_required

User = get_user_model()


@super_admin_required
def users_list(request):
    search = (request.GET.get('search') or '').strip()
    role = (request.GET.get('role') or '').strip()
    status = (request.GET.get('status') or '').strip()

    qs = (
        User.objects
        .select_related('client_profile', 'agent_profile')
        .order_by('-id')
    )
    if search:
        qs = qs.filter(
            Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )
    if role:
        qs = qs.filter(role=role)
    if status:
        qs = qs.filter(status=status)

    page = Paginator(qs, 50).get_page(request.GET.get('page'))
    return render(request, 'super_admin/users/list.html', {
        'page_title': 'Users',
        'page_obj': page,
        'total_count': qs.count(),
        'roles': User.Role.choices,
        'statuses': User.Status.choices,
        'search': search,
        'selected_role': role,
        'selected_status': status,
    })
