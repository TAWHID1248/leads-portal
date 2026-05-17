from django.shortcuts import render

from apps.accounts.decorators import super_admin_required


@super_admin_required
def dashboard(request):
    return render(request, 'super_admin/dashboard.html', {
        'portal_name': 'Super Admin',
        'page_title': 'Dashboard',
    })
