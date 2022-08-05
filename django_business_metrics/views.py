import prometheus_client
from django.http import HttpResponse, HttpRequest

from .collector import BUSINESS_METRICS_COLLECTOR


def business_metrics_view(request: HttpRequest) -> HttpResponse:
    return HttpResponse(
        prometheus_client.generate_latest(BUSINESS_METRICS_COLLECTOR),
        content_type=prometheus_client.CONTENT_TYPE_LATEST
    )
