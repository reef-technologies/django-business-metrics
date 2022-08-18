from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Iterable, Callable, Dict

from prometheus_client.registry import Collector
from prometheus_client.metrics_core import GaugeMetricFamily
from django.http import HttpRequest, HttpResponse

import prometheus_client


@dataclass
class _BusinessMetric:
    name: str
    documentation: str
    callable: Callable[[], float]


def _get_gauge_metric(metric: _BusinessMetric) -> GaugeMetricFamily:
    return GaugeMetricFamily(
        name=metric.name,
        documentation=metric.documentation,
        value=metric.callable())


class _BusinessMetricsCollector(Collector):
    _metrics: Dict[str, _BusinessMetric]
    thread_pool_size: int

    def __init__(self, thread_pool_size=5):
        self._metrics = {}
        self.thread_pool_size = thread_pool_size

    def add(self, metric: _BusinessMetric):
        if metric.name in self._metrics:
            raise ValueError(f"Business metric with name {metric.name} already exists")
        self._metrics[metric.name] = metric
        return self

    def collect(self) -> Iterable[GaugeMetricFamily]:
        with ThreadPoolExecutor(max_workers=self.thread_pool_size) as pool:
            return pool.map(_get_gauge_metric, self._metrics.values())


class BusinessMetricsManager:
    _collector: _BusinessMetricsCollector

    def __init__(self, thread_pool_size=5):
        self._collector = _BusinessMetricsCollector(thread_pool_size=thread_pool_size)

    def add(self, func: Callable[[], float], name=None, documentation=""):
        metric = _BusinessMetric(
            name=name or func.__name__,
            documentation=documentation,
            callable=func
        )
        self._collector.add(metric)
        return self

    def metric(self, name=None, documentation=""):
        def metric_decorator(func: Callable[[], float]):
            self.add(func, name or func.__name__, documentation=documentation)
            return func
        return metric_decorator

    def view(self, request: HttpRequest) -> HttpResponse:
        return HttpResponse(
            prometheus_client.generate_latest(self._collector),
            content_type=prometheus_client.CONTENT_TYPE_LATEST
        )
