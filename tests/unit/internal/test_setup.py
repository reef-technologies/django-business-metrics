"""
Basic test environment setup test.
It should always pass as long as all dependencies are properly installed.
"""

from datetime import datetime, timedelta

import pytest
from freezegun import freeze_time


def test__setup():
    with freeze_time(datetime.now() - timedelta(days=1)):
        pass

    with pytest.raises(ZeroDivisionError):
        1 / 0
