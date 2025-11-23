"""
test_browser_pool.py

Test suite for Scrapesome's synchronous and asynchronous Playwright browser
context pools.

The tests ensure:
    • Correct initialization of sync & async browser pools
    • acquire_context() and release_context() behavior
    • Timeout handling
    • Proper cleanup in close()
    • Propagation of initialization errors via ScraperError
    • async factory method AsyncBrowserPool.create()

All Playwright APIs are fully mocked: no real browsers are launched.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from scrapesome.exceptions import ScraperError
from scrapesome.utils.browser_pool import SyncBrowserPool, AsyncBrowserPool


@patch("scrapesome.utils.browser_pool.sync_playwright")
def test_sync_pool_initializes_contexts(mock_sync_playwright):
    """
    Verify that SyncBrowserPool initializes the correct number of contexts.
    """
    mock_pw = mock_sync_playwright.return_value.start.return_value
    mock_browser = mock_pw.chromium.launch.return_value

    ctx1, ctx2 = MagicMock(), MagicMock()
    mock_browser.new_context.side_effect = [ctx1, ctx2]

    pool = SyncBrowserPool(pool_size=2)

    assert len(pool._contexts) == 2
    assert pool._contexts == [ctx1, ctx2]


@patch("scrapesome.utils.browser_pool.sync_playwright")
def test_sync_acquire_and_release(mock_sync_playwright):
    """
    Test that acquiring removes a context from the pool and releasing returns it.
    """
    mock_pw = mock_sync_playwright.return_value.start.return_value
    mock_browser = mock_pw.chromium.launch.return_value

    ctx1, ctx2 = MagicMock(), MagicMock()
    mock_browser.new_context.side_effect = [ctx1, ctx2]

    pool = SyncBrowserPool(pool_size=2)

    acquired = pool.acquire_context()
    assert acquired in (ctx1, ctx2)
    assert len(pool._contexts) == 1

    pool.release_context(acquired)
    assert len(pool._contexts) == 2


@patch("scrapesome.utils.browser_pool.sync_playwright")
def test_sync_acquire_timeout(mock_sync_playwright):
    """
    If no contexts are available, acquire_context(timeout=X) raises ScraperError.
    """
    mock_pw = mock_sync_playwright.return_value.start.return_value
    mock_browser = mock_pw.chromium.launch.return_value

    mock_browser.new_context.return_value = MagicMock()

    pool = SyncBrowserPool(pool_size=1)

    ctx = pool.acquire_context()  # now pool is empty

    with pytest.raises(ScraperError):
        pool.acquire_context(timeout=0.05)

    # release so pool can close cleanly
    pool.release_context(ctx)


@patch("scrapesome.utils.browser_pool.sync_playwright")
def test_sync_pool_close(mock_sync_playwright):
    """
    Verify SyncBrowserPool.close() closes contexts, the browser, and Playwright.
    """
    mock_pw = MagicMock()
    mock_sync_playwright.return_value.start.return_value = mock_pw

    mock_browser = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser

    ctx1, ctx2 = MagicMock(), MagicMock()
    mock_browser.new_context.side_effect = [ctx1, ctx2]

    pool = SyncBrowserPool(pool_size=2)
    pool.close()

    ctx1.close.assert_called_once()
    ctx2.close.assert_called_once()
    mock_browser.close.assert_called_once()
    mock_pw.stop.assert_called_once()


@patch("scrapesome.utils.browser_pool.sync_playwright")
def test_sync_pool_initialization_error(mock_sync_playwright):
    """
    If Playwright fails to start, SyncBrowserPool should raise ScraperError.
    """
    mock_sync_playwright.return_value.start.side_effect = RuntimeError("boom")

    with pytest.raises(ScraperError):
        SyncBrowserPool(pool_size=1)


@pytest.mark.asyncio
@patch("scrapesome.utils.browser_pool.async_playwright")
async def test_async_pool_initializes_contexts(mock_async_playwright):
    """
    Verify Basic async pool initialization and context creation.
    """
    # async_playwright().start() must return awaitable
    mock_pw = AsyncMock()
    mock_async_playwright.return_value.start = AsyncMock(return_value=mock_pw)

    # browser.launch must be awaitable
    mock_browser = AsyncMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

    # contexts must be awaitable
    ctx1, ctx2 = AsyncMock(), AsyncMock()
    mock_browser.new_context = AsyncMock(side_effect=[ctx1, ctx2])

    pool = await AsyncBrowserPool.create(pool_size=2)

    assert len(pool._contexts) == 2
    assert pool._contexts == [ctx1, ctx2]


@pytest.mark.asyncio
@patch("scrapesome.utils.browser_pool.async_playwright")
async def test_async_acquire_and_release(mock_async_playwright):
    """
    Verify acquiring and releasing async contexts updates pool correctly.
    """
    mock_pw = AsyncMock()
    mock_async_playwright.return_value.start = AsyncMock(return_value=mock_pw)

    mock_browser = AsyncMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

    ctx1, ctx2 = AsyncMock(), AsyncMock()
    mock_browser.new_context = AsyncMock(side_effect=[ctx1, ctx2])

    pool = await AsyncBrowserPool.create(pool_size=2)

    acquired = await pool.acquire_context()
    assert acquired in (ctx1, ctx2)
    assert len(pool._contexts) == 1

    await pool.release_context(acquired)
    assert len(pool._contexts) == 2


@pytest.mark.asyncio
@patch("scrapesome.utils.browser_pool.async_playwright")
async def test_async_acquire_timeout(mock_async_playwright):
    """
    Timeout during acquire_context(timeout=X) must raise ScraperError.
    """
    mock_pw = AsyncMock()
    mock_async_playwright.return_value.start = AsyncMock(return_value=mock_pw)

    mock_browser = AsyncMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

    ctx = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=ctx)

    pool = await AsyncBrowserPool.create(pool_size=1)

    acquired = await pool.acquire_context()  # empty the pool

    with pytest.raises(ScraperError):
        await pool.acquire_context(timeout=0.05)

    await pool.release_context(acquired)


@pytest.mark.asyncio
@patch("scrapesome.utils.browser_pool.async_playwright")
async def test_async_pool_close(mock_async_playwright):
    """
    Verify AsyncBrowserPool.close() closes contexts, browser, and Playwright.
    """
    mock_pw = AsyncMock()
    mock_async_playwright.return_value.start = AsyncMock(return_value=mock_pw)

    mock_browser = AsyncMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

    ctx1, ctx2 = AsyncMock(), AsyncMock()
    mock_browser.new_context = AsyncMock(side_effect=[ctx1, ctx2])

    pool = await AsyncBrowserPool.create(pool_size=2)
    await pool.close()

    ctx1.close.assert_awaited()
    ctx2.close.assert_awaited()
    mock_browser.close.assert_awaited()
    mock_pw.stop.assert_awaited()


@pytest.mark.asyncio
@patch("scrapesome.utils.browser_pool.async_playwright")
async def test_async_pool_initialization_error(mock_async_playwright):
    """
    If async_playwright().start() fails, AsyncBrowserPool.create() must raise ScraperError.
    """
    mock_async_playwright.return_value.start = AsyncMock(side_effect=RuntimeError("fail"))

    with pytest.raises(ScraperError):
        await AsyncBrowserPool.create(pool_size=1)
