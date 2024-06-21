import pytest


@pytest.mark.django_db
def test_users_n_active_users(apiver_module, user_model):
    assert apiver_module.users() == 0
    assert apiver_module.active_users() == 0
    user_model.objects.create(username="test")
    assert apiver_module.users() == 1
    assert apiver_module.active_users() == 1
    user_model.objects.create(username="test2", is_active=False)
    assert apiver_module.users() == 2
    assert apiver_module.active_users() == 1
