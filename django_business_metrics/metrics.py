from django.contrib.auth.models import User

def user_count_metric() -> int:
    return float(User.objects.count())