"""
test_rendering.py

Test suite for the Scrapesome JavaScript rendering module after refactoring
to use SyncBrowserPool and AsyncBrowserPool instead of direct Playwright
usage.

This suite verifies:

    • Request-blocking helper `_should_block`
    • Synchronous JS rendering
    • Asynchronous JS rendering
    • Timeout fallback behavior (networkidle → domcontentloaded)
    • Proper raising of ScraperError on unexpected failures
    • Cleanup of pages, contexts, and pools

The Playwright layer is intentionally NOT mocked — only the browser pool
interfaces are mocked because the rendering module now depends exclusively
on them.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from scrapesome.scraper import rendering
from scrapesome.exceptions import ScraperError

@pytest.mark.parametrize("resource_type,url,expected", [
    ("image", "https://example.com/a.jpg", True),
    ("media", "https://example.com/video.mp4", True),
    ("font", "https://example.com/font.woff", True),
    ("script", "https://ads.example.com/tracker.js", True),
    ("script", "https://example.com/main.js", False),
    ("document", "https://example.com", False),
])
def test_should_block(resource_type, url, expected):
    """
    Verify the helper `_should_block` correctly identifies ad/media/image
    resources and returns the expected boolean output.
    """
    assert rendering._should_block(url, resource_type) is expected


# ---------------------------------------------------------------------
# Synchronous rendering tests
# ---------------------------------------------------------------------

@patch("scrapesome.scraper.rendering.SyncBrowserPool")
def test_sync_render_page_success(MockPool):
    """
    Test successful synchronous JavaScript rendering.

    Ensures:
        • Goto is called with networkidle
        • Returned content matches mock
        • Page and context are cleaned up
    """
    mock_pool = MockPool.return_value
    mock_context = MagicMock()
    mock_page = MagicMock()

    mock_pool.acquire_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    mock_page.goto.return_value = None
    mock_page.content.return_value = "<html>mocked content</html>"

    result = rendering.sync_render_page("https://example.com", timeout=1)

    assert result == "<html>mocked content</html>"
    mock_page.goto.assert_called_with("https://example.com", wait_until="networkidle", timeout=1000)
    mock_page.close.assert_called_once()
    mock_pool.release_context.assert_called_once()


@patch("scrapesome.scraper.rendering.SyncBrowserPool")
def test_sync_render_page_timeout_fallback(MockPool):
    """
    Test sync fallback behavior: networkidle → domcontentloaded.

    Simulates networkidle timeout error (`SyncTimeoutError`)
    followed by a successful second goto().
    """
    mock_pool = MockPool.return_value
    mock_context = MagicMock()
    mock_page = MagicMock()

    mock_pool.acquire_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    SyncTimeoutError = rendering.SyncTimeoutError

    mock_page.goto.side_effect = [SyncTimeoutError("timeout"), None]
    mock_page.content.return_value = "<html>fallback</html>"

    result = rendering.sync_render_page("https://example.com", timeout=1)

    assert result == "<html>fallback</html>"
    assert mock_page.goto.call_count == 2
    mock_page.goto.assert_any_call("https://example.com", wait_until="networkidle", timeout=1000)
    mock_page.goto.assert_any_call("https://example.com", wait_until="domcontentloaded", timeout=1000)


@patch("scrapesome.scraper.rendering.SyncBrowserPool")
def test_sync_render_page_raises_scraper_error(MockPool):
    """
    Ensure unexpected synchronous rendering errors raise `ScraperError`.

    Here, acquiring a context fails, simulating a lower-level pool failure.
    """
    MockPool.return_value.acquire_context.side_effect = RuntimeError("pool fail")

    with pytest.raises(ScraperError):
        rendering.sync_render_page("https://example.com", timeout=1)


# ---------------------------------------------------------------------
# Asynchronous rendering tests
# ---------------------------------------------------------------------

@pytest.mark.asyncio
@patch("scrapesome.scraper.rendering.AsyncBrowserPool")
async def test_async_render_page_success(MockPoolClass):
    """
    Test successful asynchronous JavaScript rendering.
    """
    # Mock returned pool instance
    mock_pool = AsyncMock()
    MockPoolClass.create = AsyncMock(return_value=mock_pool)

    mock_context = AsyncMock()
    mock_page = AsyncMock()

    mock_pool.acquire_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    mock_page.goto.return_value = None
    mock_page.content.return_value = "<html>async mocked</html>"

    result = await rendering.async_render_page("https://example.com", timeout=1)

    assert result == "<html>async mocked</html>"
    mock_page.goto.assert_called_with("https://example.com", wait_until="networkidle", timeout=1000)
    mock_page.close.assert_awaited()
    mock_pool.release_context.assert_awaited()


@pytest.mark.asyncio
@patch("scrapesome.scraper.rendering.AsyncBrowserPool")
async def test_async_render_page_timeout_fallback(MockPoolClass):
    """
    Test async fallback behavior: networkidle timeout → domcontentloaded.
    """
    mock_pool = AsyncMock()
    MockPoolClass.create = AsyncMock(return_value=mock_pool)

    mock_context = AsyncMock()
    mock_page = AsyncMock()

    mock_pool.acquire_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    AsyncTimeoutError = rendering.AsyncTimeoutError

    async def goto_side_effect(*args, **kwargs):
        if goto_side_effect.calls == 0:
            goto_side_effect.calls += 1
            raise AsyncTimeoutError("timeout")
        return None

    goto_side_effect.calls = 0
    mock_page.goto.side_effect = goto_side_effect
    mock_page.content.return_value = "<html>async fallback</html>"

    result = await rendering.async_render_page("https://example.com", timeout=1)

    assert result == "<html>async fallback</html>"
    assert mock_page.goto.call_count == 2
    mock_page.goto.assert_any_call("https://example.com", wait_until="networkidle", timeout=1000)
    mock_page.goto.assert_any_call("https://example.com", wait_until="domcontentloaded", timeout=1000)
    mock_page.close.assert_awaited()


@pytest.mark.asyncio
@patch("scrapesome.scraper.rendering.AsyncBrowserPool")
async def test_async_render_page_raises_scraper_error(MockPool):
    """
    Ensure unexpected async rendering errors raise `ScraperError`.

    Here, acquiring a context triggers a low-level failure.
    """
    MockPool.return_value.acquire_context.side_effect = RuntimeError("pool explode")

    with pytest.raises(ScraperError):
        await rendering.async_render_page("https://example.com", timeout=1)
