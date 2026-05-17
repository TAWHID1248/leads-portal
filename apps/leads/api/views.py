from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.leads.api.authentication import IngestApiKeyAuthentication
from apps.leads.api.serializers import LeadIngestSerializer
from apps.leads.services.ingest import ingest_lead
from apps.notifications.models import ActivityLog


def _client_ip(request):
    fwd = request.META.get('HTTP_X_FORWARDED_FOR')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class LeadIngestView(APIView):
    authentication_classes = [IngestApiKeyAuthentication]
    permission_classes = [permissions.AllowAny]
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        serializer = LeadIngestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated = serializer.validated_data
        ip = _client_ip(request)
        if ip and not validated.get('ip_address'):
            validated['ip_address'] = ip
        ua = request.META.get('HTTP_USER_AGENT')
        if ua and not validated.get('user_agent'):
            validated['user_agent'] = ua

        lead = ingest_lead(validated)

        try:
            ActivityLog.objects.create(
                user=None,
                action='lead.ingested',
                entity_type='Lead',
                entity_id=str(lead.id),
                metadata={
                    'leadId': lead.id,
                    'niche': lead.niche,
                    'status': lead.status,
                    'ip': ip,
                },
                ip_address=ip,
            )
        except Exception:
            pass

        return Response(
            {'leadId': lead.id, 'status': lead.status},
            status=status.HTTP_201_CREATED,
        )
