from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

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
    _metrics: dict[str, _BusinessMetric]
    _concurrent_collections: int
    _timeout: float

    def __init__(self, concurrent_collections: int, timeout: float):
        self._metrics = {}
        self._concurrent_collections = concurrent_collections
        self._timeout = timeout

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
        with ThreadPoolExecutor(max_workers=self._concurrent_collections) as pool:
            return pool.map(
                self._map_metric, self._metrics.values(), timeout=self._timeout
            )


class BusinessMetricsManager:
    """BusinessMetricsManager collects and formats business metrics."""

    _collector: _BusinessMetricsCollector

    def __init__(self, concurrent_collections: int = 5, timeout=10):
        """
        concurrent_collections - how many metrics should be collected concurrently at a time.
        timeout - timeout of the metrics collection.
        """
        self._collector = _BusinessMetricsCollector(concurrent_collections, timeout)

    def add(self, callable: Callable[[], float], name=None, documentation=""):
        """Add a metric."""
        metric = _BusinessMetric(
            name=name or callable.__name__,
            documentation=documentation,
            callable=callable,
        )
        self._collector.add(metric)
        return self

    def metric(self, name: str | None = None, documentation: str = ""):
        """A decorator that marks a function as a metric.

        Example use:
        ```
        @metric_manager.metric(name='my_metric_name', documentation='My documentation')
        def my_metric():
            return 1
        ```

        Parameters:
        name - name or the metric. If not provided, function name will be used.
        documentation - description of the metric. Optional.
        """

        def metric_decorator(callable: Callable[[], float]):
            self.add(callable, name or callable.__name__, documentation=documentation)
            return callable

        return metric_decorator

    def view(self, _: HttpRequest) -> HttpResponse:
        """Django view that returns a Prometheus-compatable metrics scrape page."""
        return HttpResponse(
            prometheus_client.generate_latest(self._collector),
            content_type=prometheus_client.CONTENT_TYPE_LATEST,
        )
