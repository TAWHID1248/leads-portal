from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import super_admin_required
from apps.groups.models import FacebookGroup


@super_admin_required
def facebook_groups_list(request):
    q = request.GET.get('q', '').strip()
    groups = FacebookGroup.objects.select_related('added_by')
    if q:
        groups = groups.filter(name__icontains=q)
    return render(request, 'super_admin/facebook_groups.html', {
        'page_title': 'Facebook Groups',
        'groups': groups,
        'total': FacebookGroup.objects.count(),
        'q': q,
    })


@super_admin_required
def facebook_group_create(request):
    if request.method == 'POST':
        group = _save_group(request, FacebookGroup())
        if group:
            messages.success(request, f'Group "{group.name}" added.')
            return redirect('super_admin:facebook_groups')
    return render(request, 'super_admin/facebook_group_form.html', {
        'page_title': 'Add Facebook Group',
        'group': None,
        'type_choices': FacebookGroup.GroupType.choices,
        'quality_choices': FacebookGroup.Quality.choices,
    })


@super_admin_required
def facebook_group_edit(request, pk):
    group = get_object_or_404(FacebookGroup, pk=pk)
    if request.method == 'POST':
        updated = _save_group(request, group)
        if updated:
            messages.success(request, f'Group "{updated.name}" updated.')
            return redirect('super_admin:facebook_groups')
    return render(request, 'super_admin/facebook_group_form.html', {
        'page_title': 'Edit Facebook Group',
        'group': group,
        'type_choices': FacebookGroup.GroupType.choices,
        'quality_choices': FacebookGroup.Quality.choices,
    })


@super_admin_required
@require_POST
def facebook_group_delete(request, pk):
    group = get_object_or_404(FacebookGroup, pk=pk)
    name = group.name
    group.delete()
    messages.success(request, f'Group "{name}" deleted.')
    return redirect('super_admin:facebook_groups')


def _save_group(request, group):
    name = request.POST.get('name', '').strip()
    if not name:
        return None
    group.name       = name
    group.group_url  = request.POST.get('group_url', '').strip()
    group.group_type = request.POST.get('group_type', FacebookGroup.GroupType.DATA_LEADS)
    group.members    = int(request.POST.get('members', 0) or 0)
    group.is_active  = request.POST.get('is_active') == 'on'
    group.quality    = request.POST.get('quality', FacebookGroup.Quality.AVERAGE)
    group.owner_name = request.POST.get('owner_name', '').strip()
    group.owner_url  = request.POST.get('owner_url', '').strip()
    group.admin_1    = request.POST.get('admin_1', '').strip()
    group.admin_2    = request.POST.get('admin_2', '').strip()
    group.admin_3    = request.POST.get('admin_3', '').strip()
    group.agent_name = request.POST.get('agent_name', '').strip()
    group.backup_url = request.POST.get('backup_url', '').strip()
    if not group.pk:
        group.added_by = request.user
    group.save()
    return group
