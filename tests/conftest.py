"""Common fixtures and steps."""

import pytest


@pytest.fixture(scope="session", autouse=True)
def tdm():
    pass
    # proc = subprocess.Popen(...)
    # request.addfinalizer(proc.kill)
