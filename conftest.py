import asyncio

import pytest


@pytest.fixture(scope='session')
def loop():
    return asyncio.get_event_loop()


@pytest.fixture
def run_sync(loop):
    return loop.run_until_complete
