from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render


def not_found_view(request, exception=None):
    return render(request, '404.html', status=404)


def healthz(request):
    """Lightweight health probe — pings the DB and returns 200."""
    try:
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
        return JsonResponse({'status': 'ok'})
    except Exception as exc:
        return JsonResponse({'status': 'error', 'detail': str(exc)}, status=503)
