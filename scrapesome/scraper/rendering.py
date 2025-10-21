"""
JavaScript Rendering Module for Scrapesome
------------------------------------------

This module provides functions to render JavaScript-heavy web pages using Playwright.
It supports both synchronous and asynchronous rendering modes with browser pooling.

Features:
    - Renders pages that require JavaScript execution.
    - Falls back from 'networkidle' to 'domcontentloaded' if initial wait fails.
    - Blocks images and known ad providers to reduce bandwidth and speed up rendering.
    - Supports custom headers, timeout configuration, and context reuse via browser pooling.

Usage:
    from scrapesome.scraper.rendering import sync_render_page, async_render_page
"""

import random
from typing import Optional, List
from playwright.sync_api import TimeoutError as SyncTimeoutError
from playwright.async_api import TimeoutError as AsyncTimeoutError
from scrapesome.utils.browser_pool import SyncBrowserPool, AsyncBrowserPool
from scrapesome.logging import get_logger
from scrapesome.config import Settings
from scrapesome.exceptions import ScraperError

settings = Settings()
logger = get_logger()


def _should_block(request_url: str, resource_type: str) -> bool:
    """
    Helper to decide whether a request should be blocked.

    Args:
        request_url (str): The URL of the request.
        resource_type (str): The type of resource being requested.

    Returns:
        bool: True if request should be blocked, False otherwise.
    """
    blocked_resources = {"image", "media", "font"}
    return resource_type in blocked_resources or "ads" in request_url


def sync_render_page(url: str, headers: Optional[dict] = None, timeout: int = int(settings.fetch_playwright_timeout), user_agents: Optional[List[str]] = None) -> str:
    """
    Renders the given URL using synchronous Playwright with headless Chromium
    via browser pooling.

    Args:
        url (str): URL to render.
        headers (Optional[dict]): Optional request headers.
        timeout (int): Timeout in seconds for page load.
        user_agents (Optional[List[str]]): List of user agents to rotate.

    Returns:
        str: Rendered HTML content of the page.

    Raises:
        ScraperError: If page rendering fails.
    """
    pool = SyncBrowserPool()
    context = None
    try:
        # Acquire a pre-created browser context from the pool
        context = pool.acquire_context()
        context_args = {}
        context_args["java_script_enabled"] = True
        if user_agents:
            context_args["user_agent"] = random.choice(user_agents)

        page = context.new_page()
        if headers:
            page.set_extra_http_headers(headers)

        # Block images and ads for performance
        context.route("**/*", lambda route, request: route.abort()
                      if _should_block(request.url, request.resource_type)
                      else route.continue_())

        try:
            page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
        except SyncTimeoutError:
            logger.warning(f"Timeout with 'networkidle'. Retrying with 'domcontentloaded' for {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)

        content = page.content()
        logger.info(f"Synchronous JS rendering completed for: {url}")
        return content

    except Exception as e:
        logger.exception(e)
        logger.error(f"Playwright sync rendering failed for {url}: {e}")
        raise ScraperError(f"Sync rendering failed for {url}") from e

    finally:
        # Release the context back to the pool
        if context:
            try:
                pool.release_context(context)
            except Exception as e:
                logger.warning(f"Failed to release sync context for {url}: {e}")


async def async_render_page(
    url: str,
    headers: Optional[dict] = None,
    timeout: int = int(settings.fetch_playwright_timeout),
    user_agents: Optional[List[str]] = None
) -> str:
    """
    Renders the given URL using asynchronous Playwright with headless Chromium
    via browser pooling.

    Args:
        url (str): URL to render.
        headers (Optional[dict]): Optional request headers.
        timeout (int): Timeout in seconds for page load.
        user_agents (Optional[List[str]]): List of user agents to rotate.

    Returns:
        str: Rendered HTML content of the page.

    Raises:
        ScraperError: If page rendering fails.
    """
    pool = await AsyncBrowserPool.get_instance()
    context = None
    try:
        # Acquire a pre-created async browser context from the pool
        context = await pool.acquire_context()
        context_args = {}
        context_args["java_script_enabled"] = True
        if user_agents:
            context_args["user_agent"] = random.choice(user_agents)

        page = await context.new_page()
        if headers:
            await page.set_extra_http_headers(headers)

        # Block images and ads for performance
        await context.route("**/*", lambda route, request: route.abort()
                            if _should_block(request.url, request.resource_type)
                            else route.continue_())

        try:
            await page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
        except AsyncTimeoutError:
            logger.warning(f"Timeout with 'networkidle'. Retrying with 'domcontentloaded' for {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)

        content = await page.content()
        logger.info(f"Asynchronous JS rendering completed for: {url}")
        return content

    except Exception as e:
        logger.exception(e)
        logger.error(f"Playwright async rendering failed for {url}: {e}")
        raise ScraperError(f"Async rendering failed for {url}") from e

    finally:
        # Release the async context back to the pool
        if context:
            try:
                await pool.release_context(context)
            except Exception as e:
                logger.warning(f"Failed to release async context for {url}: {e}")
