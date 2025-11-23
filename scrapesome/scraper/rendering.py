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
import asyncio
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


def sync_render_page(
    url: str,
    headers: Optional[dict] = None,
    timeout: int = int(settings.fetch_playwright_timeout),
    user_agents: Optional[List[str]] = None,
    pool: Optional[SyncBrowserPool] = None
) -> str:
    """
    Render URL using synchronous Playwright via a SyncBrowserPool.

    Args:
        url: URL to render.
        headers: Optional request headers.
        timeout: Timeout seconds.
        user_agents: Optional list to rotate User-Agent header.
        pool: Optional SyncBrowserPool instance. If None, a temporary pool (size=1) is created.

    Returns:
        Rendered HTML content.

    Raises:
        ScraperError on failure.
    """
    local_pool = None
    context = None
    page = None
    try:
        # prepare pool (use provided or create temp pool of size 1)
        if pool is None:
            local_pool = SyncBrowserPool(pool_size=int(settings.browser_pool_size))
            pool_to_use = local_pool
        else:
            pool_to_use = pool

        context = pool_to_use.acquire_context()
        # create a page per-request and apply headers/UA on the page
        page = context.new_page()

        effective_headers = dict(headers or {})
        if user_agents:
            effective_headers["User-Agent"] = random.choice(user_agents)
        if effective_headers:
            page.set_extra_http_headers(effective_headers)

        # sync route handler
        def _route_handler(route, request):
            try:
                if _should_block(request.url, request.resource_type):
                    route.abort()
                else:
                    route.continue_()
            except Exception:
                try:
                    route.continue_()
                except Exception:
                    pass

        context.route("**/*", _route_handler)

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
        # close page, release context, and close local pool if created
        try:
            if page:
                page.close()
        except Exception:
            logger.debug("Failed to close sync page", exc_info=True)
        if context:
            try:
                pool_to_use.release_context(context)
            except Exception:
                logger.warning(f"Failed to release sync context for {url}")
        if local_pool:
            try:
                local_pool.close()
            except Exception:
                logger.debug("Failed to close temporary sync pool", exc_info=True)


async def async_render_page(
    url: str,
    headers: Optional[dict] = None,
    timeout: int = int(settings.fetch_playwright_timeout),
    user_agents: Optional[List[str]] = None,
    pool: Optional[AsyncBrowserPool] = None
) -> str:
    """
    Render URL using async Playwright via an AsyncBrowserPool.

    Args:
        url: URL to render.
        headers: Optional request headers.
        timeout: Timeout seconds.
        user_agents: Optional list to rotate User-Agent header.
        pool: Optional AsyncBrowserPool instance. If None, a temporary pool (size=1) is created.

    Returns:
        Rendered HTML content.

    Raises:
        ScraperError on failure.
    """
    local_pool = None
    context = None
    page = None
    try:
        # prepare pool (use provided or create a temp pool of size 1)
        if pool is None:
            local_pool = await AsyncBrowserPool.create(pool_size=int(settings.browser_pool_size))
            pool_to_use = local_pool
        else:
            pool_to_use = pool

        context = await pool_to_use.acquire_context()

        page = await context.new_page()

        effective_headers = dict(headers or {})
        if user_agents:
            effective_headers["User-Agent"] = random.choice(user_agents)
        if effective_headers:
            await page.set_extra_http_headers(effective_headers)

        # async route handler
        async def _route_handler(route, request):
            try:
                if _should_block(request.url, request.resource_type):
                    await route.abort()
                else:
                    await route.continue_()
            except Exception:
                try:
                    await route.continue_()
                except Exception:
                    pass

        await context.route("**/*", _route_handler)

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
        # close page, release context, and close local pool if created
        try:
            if page:
                await page.close()
        except Exception:
            logger.debug("Failed to close async page", exc_info=True)
        if context:
            try:
                await pool_to_use.release_context(context)
            except Exception:
                logger.warning(f"Failed to release async context for {url}")
        if local_pool:
            try:
                await local_pool.close()
            except Exception:
                logger.debug("Failed to close temporary async pool", exc_info=True)
