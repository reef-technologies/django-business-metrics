import pytest

from django_business_metrics.v0 import BusinessMetricsManager, users


@pytest.fixture
def metrics_manager():
    return BusinessMetricsManager()


@pytest.fixture
def user_metric(metrics_manager):
    return metrics_manager.add(users)


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
