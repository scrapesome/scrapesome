"""
browser_pool.py

Minimal Playwright browser-context pools for Scrapesome.

Design:
  - Simple list-based pools (pop/append) like the pattern used in scraper.py.
  - No singletons, no atexit, no cross-loop tricks.
  - Explicit lifecycle: create -> acquire/release -> close.
  - Caller is responsible for concurrency control (Semaphore) as in scraper.py.
"""

from __future__ import annotations

import time
import asyncio
from typing import List, Optional

# sync/async Playwright APIs
from playwright.sync_api import sync_playwright, BrowserContext
from playwright.async_api import async_playwright, BrowserContext as AsyncBrowserContext

from scrapesome.logging import get_logger
from scrapesome.config import Settings
from scrapesome.exceptions import ScraperError

settings = Settings()
logger = get_logger()


class SyncBrowserPool:
    """
    Minimal synchronous browser context pool.

    Usage (same style as your scraper.py):
        pool = SyncBrowserPool(pool_size=2)
        ctx = pool.acquire_context()          # blocks until available
        page = ctx.new_page()
        ...
        page.close()
        pool.release_context(ctx)
        pool.close()
    """

    def __init__(self, pool_size: Optional[int] = None):
        self.pool_size = pool_size or getattr(settings, "browser_pool_size", 2)
        self._playwright = None
        self._browser = None
        self._contexts: List[BrowserContext] = []
        self._closed = False
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        try:
            logger.info(f"Initializing SyncBrowserPool (size={self.pool_size})")
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            for i in range(self.pool_size):
                ctx = self._browser.new_context(java_script_enabled=True)
                self._contexts.append(ctx)
                logger.info(f"Sync context created {i+1}/{self.pool_size}")
        except Exception as e:
            logger.exception("Failed to initialize SyncBrowserPool")
            try:
                self.close()
            except Exception:
                pass
            raise ScraperError(f"Sync browser pool initialization failed: {e}") from e

    def acquire_context(self, timeout: Optional[float] = None) -> BrowserContext:
        """
        Pop and return a context. If timeout is None, block until available.
        If timeout is provided (seconds), wait up to that long polling periodically.
        """
        if self._closed:
            raise ScraperError("SyncBrowserPool is closed")

        end = None if timeout is None else time.monotonic() + float(timeout)
        while True:
            if self._contexts:
                ctx = self._contexts.pop()
                logger.info("Acquired synchronous browser context from pool")
                return ctx
            if end is not None and time.monotonic() >= end:
                raise ScraperError("No available synchronous browser context in pool (timeout)")
            time.sleep(0.05)

    def release_context(self, context: BrowserContext) -> None:
        """Return the context to the pool (best-effort cleanup first)."""
        if self._closed:
            try:
                context.close()
            except Exception:
                pass
            return

        try:
            try:
                context.clear_cookies()
            except Exception:
                pass
            try:
                context.clear_permissions()
            except Exception:
                pass
            self._contexts.append(context)
            logger.info("Released synchronous browser context back to pool")
        except Exception as e:
            logger.warning(f"Failed to release sync context cleanly: {e}")
            try:
                context.close()
            except Exception:
                pass

    def close(self) -> None:
        """Close contexts, browser, and Playwright. After this pool is unusable."""
        if self._closed:
            return
        self._closed = True

        logger.info("Closing SyncBrowserPool")
        while self._contexts:
            ctx = self._contexts.pop()
            try:
                ctx.close()
            except Exception:
                logger.debug("Exception while closing sync context", exc_info=True)

        try:
            if self._browser:
                self._browser.close()
        except Exception:
            logger.debug("Exception closing sync browser", exc_info=True)
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            logger.debug("Exception stopping sync playwright", exc_info=True)

        self._browser = None
        self._playwright = None
        logger.info("SyncBrowserPool closed")


class AsyncBrowserPool:
    """
    Minimal asynchronous browser context pool.

    Usage:
        pool = await AsyncBrowserPool.create(pool_size=2)
        ctx = await pool.acquire_context()
        page = await ctx.new_page()
        ...
        await page.close()
        await pool.release_context(ctx)
        await pool.close()

    Note: concurrency control (how many tasks run at once) should be done by
    the caller, e.g. with an asyncio.Semaphore (exactly like your scraper.py).
    """

    def __init__(self, pool_size: Optional[int] = None):
        # Use the async factory `create()` to instantiate & initialize the pool.
        self.pool_size = pool_size or getattr(settings, "browser_pool_size", 2)
        self._playwright = None
        self._browser = None
        self._contexts: List[AsyncBrowserContext] = []
        self._closed = False

    @classmethod
    async def create(cls, pool_size: Optional[int] = None) -> "AsyncBrowserPool":
        """Async factory: constructs and initializes the pool."""
        self = cls(pool_size)
        await self._initialize_pool()
        return self

    async def _initialize_pool(self) -> None:
        try:
            logger.info(f"Initializing AsyncBrowserPool (size={self.pool_size})")
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
            for i in range(self.pool_size):
                ctx = await self._browser.new_context(java_script_enabled=True)
                self._contexts.append(ctx)
                logger.info(f"Async context created {i+1}/{self.pool_size}")
        except Exception as e:
            logger.exception("Failed to initialize AsyncBrowserPool")
            try:
                await self.close()
            except Exception:
                pass
            raise ScraperError(f"Async browser pool initialization failed: {e}") from e

    async def acquire_context(self, timeout: Optional[float] = None) -> AsyncBrowserContext:
        """
        Pop and return an async context. If timeout is None, wait until one available.
        If timeout is provided, wait up to that many seconds (polling).
        """
        if self._closed:
            raise ScraperError("AsyncBrowserPool is closed")

        loop = asyncio.get_event_loop()
        end = None if timeout is None else loop.time() + float(timeout)
        while True:
            if self._contexts:
                ctx = self._contexts.pop()
                logger.info("Acquired asynchronous browser context from pool")
                return ctx
            if end is not None and loop.time() >= end:
                raise ScraperError("No available asynchronous browser context in pool (timeout)")
            await asyncio.sleep(0.05)

    async def release_context(self, context: AsyncBrowserContext) -> None:
        """Return async context to pool (best-effort cleanup first)."""
        if self._closed:
            try:
                await context.close()
            except Exception:
                pass
            return

        try:
            try:
                await context.clear_cookies()
            except Exception:
                pass
            try:
                await context.clear_permissions()
            except Exception:
                pass
            self._contexts.append(context)
            logger.info("Released asynchronous browser context back to pool")
        except Exception as e:
            logger.warning(f"Failed to release async context cleanly: {e}")
            try:
                await context.close()
            except Exception:
                pass

    async def close(self) -> None:
        """Close contexts, browser, and Playwright asynchronously."""
        if self._closed:
            return
        self._closed = True

        logger.info("Closing AsyncBrowserPool")
        while self._contexts:
            ctx = self._contexts.pop()
            try:
                await ctx.close()
            except Exception:
                logger.debug("Exception while closing async context", exc_info=True)

        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            logger.debug("Exception closing async browser", exc_info=True)
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            logger.debug("Exception stopping async playwright", exc_info=True)

        self._browser = None
        self._playwright = None
        logger.info("AsyncBrowserPool closed")
