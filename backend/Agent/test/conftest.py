"""Provider smoke scripts are integration tests, never unit-test imports."""

import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.integration)
