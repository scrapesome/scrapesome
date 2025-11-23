"""
Asynchronous unit tests for the `async_scraper` function in the `scrapesome.scraper.async_scraper` module.

These tests verify correct behavior under various conditions including:
- Successful HTTP content fetch with formatting
- Fallback to JavaScript rendering when content is insufficient
- Forced Playwright rendering
- Retry mechanisms on HTTP failure and 403 status
- Custom fallback when HTTP retries are exhausted

The tests use `unittest.mock` and `pytest` to patch asynchronous dependencies with `AsyncMock` and simulate different behaviors.
"""

from unittest.mock import patch, AsyncMock
import pytest
import httpx
from scrapesome import async_scraper

# SUCCESS: HTTP response returns content and gets formatted
@patch("scrapesome.scraper.async_scraper.async_render_page", new_callable=AsyncMock)
@patch("scrapesome.scraper.async_scraper.format_response")
@patch("scrapesome.scraper.async_scraper.httpx.AsyncClient.get", new_callable=AsyncMock)
async def test_async_scraper_success_with_format(mock_get, mock_format_response, mock_render):
    """
    Test that async_scraper returns correctly formatted content when HTTP response is valid.
    """
    mock_response = AsyncMock()
    mock_response.status_code = 200
    # Return a long enough HTML content so fallback isn't triggered
    mock_response.text = "<html>" + "content " * 100 + "</html>"
    mock_get.return_value = mock_response

    mock_format_response.return_value = "Hello World"

    result = await async_scraper("http://fake.com", output_format_type="text")
    result = result.get("data")
    assert result == "Hello World"


# SUCCESS: fallback to JS rendering if content is too short
@pytest.mark.asyncio
@patch("scrapesome.scraper.async_scraper.async_render_page", new_callable=AsyncMock)
@patch("scrapesome.scraper.async_scraper.httpx.AsyncClient.get", new_callable=AsyncMock)
async def test_async_scraper_fallback_to_render(mock_get, mock_render):
    """
    Test that async_scraper falls back to JavaScript rendering when HTTP content is too short.
    """
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "Too short"
    mock_get.return_value = mock_response

    mock_render.return_value = "<html><body>Rendered Content</body></html>"

    result = await async_scraper("http://fake.com")
    result = result.get("data")
    assert "Rendered Content" in result

# SUCCESS: force Playwright rendering directly
@pytest.mark.asyncio
@patch("scrapesome.scraper.async_scraper.async_render_page", new_callable=AsyncMock)
async def test_async_scraper_force_playwright(mock_render):
    """
    Test that async_scraper uses Playwright rendering when force_playwright=True is passed.
    """
    mock_render.return_value = "<html><body>Playwright Rendered</body></html>"

    result = await async_scraper("http://fake.com", force_playwright=True)
    result = result.get("data")
    assert "Playwright Rendered" in result

# FAILURE: all retries fail, and fallback fails too
@pytest.mark.asyncio
@patch("scrapesome.scraper.async_scraper.async_render_page", side_effect=Exception("Render fail"))
@patch("scrapesome.scraper.async_scraper.httpx.AsyncClient.get", side_effect=Exception("HTTP fail"))
async def test_async_scraper_all_failures(mock_get, mock_render):
    """
    Test that async_scraper returns None when all HTTP requests and rendering attempts fail.
    """
    result = await async_scraper("http://fake.com")
    result = result.get("data")
    assert result is None


@pytest.mark.asyncio
@patch("scrapesome.scraper.async_scraper.async_render_page", new_callable=AsyncMock)
@patch("scrapesome.scraper.async_scraper.httpx.AsyncClient.get", new_callable=AsyncMock)
async def test_async_scraper_retries_on_403_then_succeeds(mock_get, mock_render):
    """
    Test that async_scraper retries after receiving a 403 and succeeds on a valid retry response.
    Ensures rendering is not triggered if retry returns successful response.
    """
    mock_403 = AsyncMock()
    mock_403.status_code = 403
    mock_403.text = "Forbidden"

    # Mock 200 response with valid content
    mock_200 = AsyncMock()
    mock_200.status_code = 200
    mock_200.text = "<html><body>" + "Recovered " * 50 + "</body></html>"

    # Side effect returns 403 first, then 200
    mock_get.side_effect = [mock_403, mock_200]

    # Call your async scraper
    result = await async_scraper("http://fake.com")
    result = result.get("data")

    # Assert recovered content found in result
    assert "Recovered" in result

    # Assert render_page was NOT called since 200 succeeded
    mock_render.assert_not_called()


# simulate multiple HTTP exceptions then fallback to render
@pytest.mark.asyncio
@patch("scrapesome.scraper.async_scraper.httpx.AsyncClient.get", new_callable=AsyncMock)
@patch("scrapesome.scraper.async_scraper.async_render_page", new_callable=AsyncMock)
async def test_async_scraper_retries_exhausted_then_render_fallback(mock_render, mock_get):
    """
    Test that async_scraper uses fallback rendering when all retry attempts result in HTTP exceptions.
    """
    mock_get.side_effect = httpx.RequestError("Request failed")
    mock_render.return_value = "<html>Fallback Render</html>"
    result = await async_scraper("http://fake.com", max_retries=2)
    result = result.get("data")
    assert "Fallback Render" in result

# short content triggers fallback to render_page
@pytest.mark.asyncio
@patch("scrapesome.scraper.async_scraper.httpx.AsyncClient.get", new_callable=AsyncMock)
@patch("scrapesome.scraper.async_scraper.async_render_page", new_callable=AsyncMock)
async def test_async_scraper_short_content_triggers_render(mock_render, mock_get):
    """
    Test that async_scraper triggers rendering fallback when HTTP response has short content.
    """
    mock_resp = AsyncMock(status_code=200, text="short")
    mock_get.return_value = mock_resp
    mock_render.return_value = "<html>Rendered Content</html>"
    result = await async_scraper("http://fake.com")
    result = result.get("data")
    assert "Rendered Content" in result

@pytest.mark.asyncio
@patch("scrapesome.scraper.async_scraper.httpx.AsyncClient.get", new_callable=AsyncMock)
async def test_async_scraper_multi_url_sequential_single_url(mock_get):
    """
    If a list of URLs is provided with less than 2 items,
    pool_size should fallback to settings.browser_pool_size.
    Ensures sequential execution.
    """
    mock_resp = AsyncMock(status_code=200, text="<html>" + ("abc " * 100) + "</html>")
    mock_get.return_value = mock_resp

    urls = ["single.com"]  # only one URL

    result = await async_scraper(urls=urls, run_concurrently=False)
    assert isinstance(result, list)
    assert len(result) == 1
    assert "abc" in result[0]["data"]

@pytest.mark.asyncio
@patch("scrapesome.scraper.async_scraper.fetch_url", side_effect=Exception("Fail"))
async def test_async_scraper_scrape_single_exception_wrapper(mock_fetch):
    """
    Ensure that _scrape_single returns a dict with 'error' key
    when fetch_url raises an exception.
    """
    from scrapesome.scraper.async_scraper import _scrape_single
    result = await _scrape_single(
        url="http://fail.com",
        user_agents=["UA"],
        headers=None,
        allow_redirects=True,
        max_retries=1,
        timeout=1,
        force_playwright=False,
        pool_size=1,
        output_format_type="text",
        file_name=None,
        save_to_file=False,
    )
    assert "error" in result
    assert "Fail" in result["error"]

@pytest.mark.asyncio
async def test_async_scraper_valueerror_url_and_urls():
    """
    Provide both url and urls should raise ValueError.
    """
    import pytest
    with pytest.raises(ValueError):
        await async_scraper(url="a.com", urls=["b.com"])

@pytest.mark.asyncio
async def test_async_scraper_valueerror_urls_not_list():
    """
    Provide urls as a non-list type should raise ValueError.
    """
    import pytest
    with pytest.raises(ValueError):
        await async_scraper(urls="not-a-list")
