import pytest
from django.contrib.auth import get_user_model
from django.db import connections


@pytest.fixture
def metrics_manager(apiver_module):
    return apiver_module.BusinessMetricsManager()


@pytest.fixture
def user_metric(apiver_module, metrics_manager):
    return metrics_manager.add(apiver_module.users)


@pytest.mark.django_db
class TestBusinessMetricsManager:
    def test_add(self, metrics_manager):
        metrics_manager.add(lambda: 0, name="name", documentation="documentation")

    def test_metric_decorator(self, metrics_manager):
        @metrics_manager.metric(name="name", documentation="documentation")
        def my_metric():
            return 10

    def test_view_response(self, request_factory, metrics_manager, user_metric):
        request = request_factory.get("/business-metrics")
        response = metrics_manager.view(request)
        assert response.status_code == 200
        assert response.content == b"# HELP users \n# TYPE users gauge\nusers 0.0\n"

    def test_view_closes_db_connections_opened_by_metrics(self, request_factory, metrics_manager):
        metric_connections = []

        @metrics_manager.metric(name="users_count")
        def users_count():
            # metrics are collected in other threads, each with its own database connection
            metric_connections.append(connections["default"])
            return get_user_model().objects.count()

        response = metrics_manager.view(request_factory.get("/business-metrics"))

        assert response.status_code == 200
        assert len(metric_connections) == 1
        assert metric_connections[0].connection is None
