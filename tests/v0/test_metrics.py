import pytest
from django_business_metrics.v0 import active_users, users


@pytest.mark.django_db
def test_users_n_active_users(user_model):
    assert users() == 0
    assert active_users() == 0
    user_model.objects.create(username="test")
    assert users() == 1
    assert active_users() == 1
    user_model.objects.create(username="test2", is_active=False)
    assert users() == 2
    assert active_users() == 1
