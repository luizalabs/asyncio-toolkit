import asyncio

import pytest


@pytest.fixture(scope='session')
def loop():
    # Set-up
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete()

    # Clean-up
    loop.close()
