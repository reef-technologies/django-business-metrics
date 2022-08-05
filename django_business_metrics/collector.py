from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Iterable, Callable, Dict

from prometheus_client.registry import Collector
from prometheus_client.metrics_core import GaugeMetricFamily


@dataclass
class BusinessMetric:
    """Full business metric definition. Meant for internal use."""
    name: str
    documentation: str
    callable: Callable[[], float]


def _get_gauge_metric(metric: BusinessMetric) -> GaugeMetricFamily:
    print(callable)
    return GaugeMetricFamily(
        name=metric.name,
        documentation=metric.documentation,
        value=metric.callable())


class BusinessMetricsCollector(Collector):
    _metrics: Dict[str, BusinessMetric]
    thread_pool_size: int

    def __init__(self, max_threads=5):
        self._metrics = {}
        self.thread_pool_size = max_threads

    def register_metric(
        self,
        name: str,
        callable: Callable[[], float],
        *,
        documentation: str="",
    ):
        self._metrics[name] = BusinessMetric(
            name=name,
            documentation=documentation,
            callable=callable
        )
        return self

    def collect(self) -> Iterable[GaugeMetricFamily]:
        with ThreadPoolExecutor(max_workers=self.thread_pool_size) as pool:
            return pool.map(_get_gauge_metric, self._metrics.values())


BUSINESS_METRICS_COLLECTOR = BusinessMetricsCollector()


def business_metric(name: str, documentation: str=""):
    """A decorator to register business metrics to BUSINESS_METRICS_COLLECTOR.

    Example use:

    @business_metric("metric_name")
    def my_metric():
        return 1
    """
    def decorator_business_metric(func: Callable[[], float]):
        BUSINESS_METRICS_COLLECTOR.register_metric(name, func, documentation=documentation)
        return func
    return decorator_business_metric
