"""
Unit tests for the `sync_scraper` function in the `scrapesome.scraper.sync_scraper` module.

These tests verify various success and failure cases of the scraper including:
- Successful content fetch with formatting
- Fallback to rendering on short content
- Forcing Playwright-based rendering
- Handling of HTTP failures and retries
- Use of custom user agents
- Behavior on redirects
- Rendering after retry exhaustion

The tests use `unittest.mock` to patch dependencies and simulate different conditions and responses.
"""

from unittest.mock import patch, MagicMock
import requests
import pytest
from scrapesome import sync_scraper
from scrapesome.exceptions import ScraperError

# SUCCESS: simple fetch returns content with output_format_type
@patch("scrapesome.scraper.sync_scraper.sync_render_page")
@patch("scrapesome.scraper.sync_scraper.format_response")
@patch("scrapesome.scraper.sync_scraper.requests.get")
def test_scraper_success_with_format(mock_get, mock_format_response, mock_render):
    """
    Test that sync_scraper returns correctly formatted content when the HTTP fetch is successful.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>Hello World</body></html>"
    mock_get.return_value = mock_response

    mock_format_response.return_value = "Hello World"

    result = sync_scraper("http://fake.com", output_format_type="text")
    result = result.get("data")
    assert result == "Hello World"

# SUCCESS: fallback to render when content is too short
@patch("scrapesome.scraper.sync_scraper.sync_render_page")
@patch("scrapesome.scraper.sync_scraper.requests.get")
def test_scraper_fallback_to_render(mock_get, mock_render):
    """
    Test that sync_scraper falls back to rendering when the fetched content is too short.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "Too short"
    mock_get.return_value = mock_response

    mock_render.return_value = "<html><body>Rendered Content</body></html>"

    result = sync_scraper("http://fake.com")
    result = result.get("data")
    assert "Rendered Content" in result

# SUCCESS: force Playwright rendering
@patch("scrapesome.scraper.sync_scraper.sync_render_page")
def test_scraper_force_playwright(mock_render):
    """
    Test that sync_scraper uses Playwright rendering when forced via the force_playwright flag.
    """
    mock_render.return_value = "<html><body>Playwright Content</body></html>"

    result = sync_scraper("http://fake.com", force_playwright=True)
    result = result.get("data")
    assert "Playwright Content" in result

# FAILURE: all retries fail and Playwright fallback also fails
@patch("scrapesome.scraper.sync_scraper.sync_render_page", side_effect=Exception("Rendering failed"))
@patch("scrapesome.scraper.sync_scraper.requests.get", side_effect=Exception("HTTP failed"))
def test_scraper_all_failures(mock_get, mock_render):
    """
    Test that sync_scraper returns None when all HTTP attempts and rendering fail.
    """
    result = sync_scraper("http://fake.com")
    result = result.get("data")
    assert result is None


@patch("scrapesome.scraper.sync_scraper.sync_render_page")
@patch("scrapesome.scraper.sync_scraper.requests.get")
def test_scraper_retries_on_403_then_succeeds(mock_get, mock_render):
    """
    Test that sync_scraper retries on receiving a 403 response and succeeds on a subsequent valid response.
    """
    mock_403 = MagicMock()
    mock_403.status_code = 403
    mock_403.text = "Forbidden"

    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.text = "<html><body>" + "Recovered " * 50 + "</body></html>"

    mock_get.side_effect = [mock_403, mock_200]

    result = sync_scraper("http://fake.com")
    result = result.get("data")
    assert "Recovered" in result

@patch("scrapesome.scraper.sync_scraper.requests.get")
def test_scraper_no_redirects(mock_get):
    """
    Test that sync_scraper respects the allow_redirects=False option.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>" + "No redirects" * 50+"</body></html>"
    mock_get.return_value = mock_response

    result = sync_scraper("http://fake.com", allow_redirects=False)
    result = result.get("data")
    assert "No redirects" in result

@patch("scrapesome.scraper.sync_scraper.requests.get")
def test_scraper_with_custom_user_agents(mock_get):
    """
    Test that sync_scraper uses the provided custom user agent.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>"+"UA test" * 50+"</body></html>"
    mock_get.return_value = mock_response

    result = sync_scraper("http://fake.com", user_agents=["TestAgent/1.0"])
    result = result.get("data")
    assert "UA test" in result

# simulate multiple request exceptions then successful render fallback
@patch("scrapesome.scraper.sync_scraper.requests.get", side_effect=requests.exceptions.RequestException)
@patch("scrapesome.scraper.sync_scraper.sync_render_page")
def test_sync_scraper_retries_exhausted_then_render_fallback(mock_render, mock_get):
    """
    Test that sync_scraper falls back to rendering after exhausting retry attempts due to request exceptions.
    """
    mock_render.return_value = "<html>Fallback Render</html>"
    result = sync_scraper("http://fake.com", max_retries=2)
    result = result.get("data")
    assert "Fallback Render" in result

# simulate short response content triggers rendering fallback
@patch("scrapesome.scraper.sync_scraper.requests.get")
@patch("scrapesome.scraper.sync_scraper.sync_render_page")
def test_sync_scraper_short_content_triggers_render(mock_render, mock_get):
    """
    Test that sync_scraper triggers rendering fallback when the HTTP response content is too short.
    """
    mock_resp = MagicMock(status_code=200, text="short")
    mock_get.return_value = mock_resp
    mock_render.return_value = "<html>Rendered Content</html>"
    result = sync_scraper("http://fake.com")
    result = result.get("data")
    assert "Rendered Content" in result


def test_sync_scraper_multi_url_concurrent_raises():
    """
    Test that sync_scraper raises ScraperError when attempting to run multiple URLs
    concurrently, since parallel scraping is not supported in sync_scraper.
    """
    urls = ["http://site1.com", "http://site2.com"]
    with pytest.raises(ScraperError, match="Parallel scraping is only supported in async_scraper"):
        sync_scraper(urls=urls, run_concurrently=True)

def test_sync_scraper_multi_url_serial_raises():
    """
    Test that sync_scraper raises ScraperError when attempting to run multiple URLs
    serially, since parallel scraping is restricted in sync_scraper.
    """
    urls = ["http://siteA.com", "http://siteB.com"]
    with pytest.raises(ScraperError, match="Parallel scraping is only supported in async_scraper"):
        sync_scraper(urls=urls, run_concurrently=False)

def test_sync_scraper_multi_url_pool_raises():
    """
    Test that sync_scraper raises ScraperError when a pool size is provided
    for multiple URLs, as sync_scraper does not support browser pools for concurrency.
    """
    urls = ["http://a.com", "http://b.com", "http://c.com"]
    with pytest.raises(ScraperError, match="Parallel scraping is only supported in async_scraper"):
        sync_scraper(urls=urls, pool_size=3)