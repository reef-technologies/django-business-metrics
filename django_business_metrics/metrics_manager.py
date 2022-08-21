from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Dict, Iterable

import prometheus_client
from django.http import HttpRequest, HttpResponse
from prometheus_client.metrics_core import GaugeMetricFamily
from prometheus_client.registry import CollectorRegistry


@dataclass
class _BusinessMetric:
    name: str
    documentation: str
    callable: Callable[[], float]


class _BusinessMetricsCollector(CollectorRegistry):
    _metrics: Dict[str, _BusinessMetric]
    concurrent_collections: int

    def __init__(self, concurrent_collections=5):
        self._metrics = {}
        self.concurrent_collections = concurrent_collections

    @staticmethod
    def _map_metric(metric: _BusinessMetric) -> GaugeMetricFamily:
        return GaugeMetricFamily(
            name=metric.name,
            documentation=metric.documentation,
            value=metric.callable(),
        )

    def add(self, metric: _BusinessMetric):
        if metric.name in self._metrics:
            raise ValueError(f"Business metric with name {metric.name} already exists")
        self._metrics[metric.name] = metric
        return self

    def collect(self) -> Iterable[GaugeMetricFamily]:
        with ThreadPoolExecutor(max_workers=self.concurrent_collections) as pool:
            return pool.map(self._map_metric, self._metrics.values())


class BusinessMetricsManager:
    _collector: _BusinessMetricsCollector

    def __init__(self, concurrent_collections: int = 5):
        self._collector = _BusinessMetricsCollector(concurrent_collections)

    def add(self, func: Callable[[], float], name=None, documentation=""):
        """Add a metric."""
        metric = _BusinessMetric(
            name=name or func.__name__, documentation=documentation, callable=func
        )
        self._collector.add(metric)
        return self

    def metric(self, name=None, documentation=""):
        """A decorator that marks a function as a metric."""

        def metric_decorator(func: Callable[[], float]):
            self.add(func, name or func.__name__, documentation=documentation)
            return func

        return metric_decorator

    def view(self, _: HttpRequest) -> HttpResponse:
        """Django view that returns a Prometheus-compatable metrics page."""
        return HttpResponse(
            prometheus_client.generate_latest(self._collector),
            content_type=prometheus_client.CONTENT_TYPE_LATEST,
        )
