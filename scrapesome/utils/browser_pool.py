"""
Playwright Browser Pool Manager for Scrapesome
----------------------------------------------

This module provides thread-safe, reusable browser context pools for Playwright.
Supports both synchronous and asynchronous modes, minimizing browser startup overhead.

Features:
    - Separate pools for synchronous and asynchronous Playwright usage.
    - Singleton pattern (one pool per process per mode).
    - Configurable pool size via settings.
    - Graceful shutdown and cleanup via atexit.
    - Safe acquire/release of browser contexts.

Usage (Synchronous):
    from scrapesome.scraper.browser_pool import SyncBrowserPool
    pool = SyncBrowserPool()
    ctx = pool.acquire_context()
    ...
    pool.release_context(ctx)

Usage (Asynchronous):
    from scrapesome.scraper.browser_pool import AsyncBrowserPool
    pool = await AsyncBrowserPool.get_instance()
    ctx = await pool.acquire_context()
    ...
    await pool.release_context(ctx)
"""

import atexit
import threading
import asyncio
from queue import Queue, Empty
from asyncio import Queue as AsyncQueue
from playwright.sync_api import sync_playwright, BrowserContext
from playwright.async_api import async_playwright, BrowserContext as AsyncBrowserContext
from scrapesome.logging import get_logger
from scrapesome.config import Settings
from scrapesome.exceptions import ScraperError

settings = Settings()
logger = get_logger()


# ==========================
# Synchronous Browser Pool
# ==========================
class SyncBrowserPool:
    """
    Singleton, thread-safe pool of synchronous Playwright Chromium browser contexts.

    Pre-creates a fixed number of browser contexts for reuse, reducing
    startup overhead when fetching multiple pages synchronously.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, pool_size: int = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, pool_size: int = None):
        if getattr(self, "_initialized", False):
            return
        self.pool_size = pool_size or getattr(settings, "browser_pool_size", 2)
        self.queue = Queue(maxsize=self.pool_size)
        self.playwright = None
        self.browser = None
        self._init_lock = threading.Lock()
        self._initialize_pool()
        atexit.register(self.close)
        self._initialized = True

    def _initialize_pool(self):
        """Initialize Playwright and pre-create browser contexts for the pool."""
        with self._init_lock:
            try:
                logger.info(f"Initializing synchronous browser pool (size={self.pool_size})")
                self.playwright = sync_playwright().start()
                self.browser = self.playwright.chromium.launch(headless=True)
                for i in range(self.pool_size):
                    ctx = self.browser.new_context(java_script_enabled=True)
                    self.queue.put(ctx)
                    logger.info(f"Created sync context {i+1}/{self.pool_size}")
            except Exception as e:
                logger.exception("Failed to initialize synchronous browser pool")
                raise ScraperError(f"Sync browser pool initialization failed: {e}") from e

    def acquire_context(self, timeout: int = 10) -> BrowserContext:
        """
        Acquire a browser context from the pool.

        Args:
            timeout (int): Time in seconds to wait for an available context.

        Returns:
            BrowserContext: Playwright browser context.

        Raises:
            ScraperError: If no context is available within the timeout.
        """
        try:
            ctx = self.queue.get(timeout=timeout)
            logger.info("Acquired synchronous browser context from pool")
            return ctx
        except Empty:
            raise ScraperError("No available synchronous browser context in pool (timeout)")

    def release_context(self, context: BrowserContext):
        """
        Release a browser context back to the pool.

        Clears cookies and permissions before reuse.

        Args:
            context (BrowserContext): Context to release.
        """
        try:
            context.clear_cookies()
            context.clear_permissions()
            self.queue.put(context)
            logger.info("Released synchronous browser context back to pool")
        except Exception as e:
            logger.warning(f"Failed to release synchronous context cleanly: {e}")
            try:
                context.close()
            except Exception:
                pass

    def close(self):
        """Shutdown the synchronous browser pool and clean up resources."""
        logger.info("Closing synchronous browser pool")
        try:
            while not self.queue.empty():
                ctx = self.queue.get_nowait()
                try:
                    ctx.close()
                except Exception:
                    pass
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.warning(f"Error during synchronous pool cleanup: {e}")


# ==========================
# Asynchronous Browser Pool
# ==========================
class AsyncBrowserPool:
    """
    Singleton, async-compatible pool of Playwright Chromium browser contexts.

    Pre-creates a fixed number of async browser contexts for reuse,
    improving performance when fetching multiple pages asynchronously.
    """
    _instance = None
    _lock = asyncio.Lock()

    def __init__(self, pool_size: int = None):
        self.pool_size = pool_size or getattr(settings, "browser_pool_size", 2)
        self.queue: AsyncQueue = AsyncQueue(maxsize=self.pool_size)
        self.playwright = None
        self.browser = None

    @classmethod
    async def get_instance(cls, pool_size: int = None):
        """
        Retrieve the singleton instance of the async browser pool.

        Args:
            pool_size (int, optional): Number of contexts in the pool.

        Returns:
            AsyncBrowserPool: Singleton async pool instance.
        """
        async with cls._lock:
            if cls._instance is None:
                instance = cls(pool_size)
                await instance._initialize_pool()
                # Schedule cleanup at exit
                atexit.register(lambda: asyncio.create_task(instance.close()))
                cls._instance = instance
        return cls._instance

    async def _initialize_pool(self):
        """Initialize async Playwright and pre-create browser contexts."""
        try:
            logger.info(f"Initializing asynchronous browser pool (size={self.pool_size})")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            for i in range(self.pool_size):
                ctx = await self.browser.new_context(java_script_enabled=True)
                await self.queue.put(ctx)
                logger.info(f"Created async context {i+1}/{self.pool_size}")
        except Exception as e:
            logger.exception("Failed to initialize asynchronous browser pool")
            raise ScraperError(f"Async browser pool initialization failed: {e}") from e

    async def acquire_context(self, timeout: int = 10) -> AsyncBrowserContext:
        """
        Acquire an async browser context from the pool.

        Args:
            timeout (int): Maximum time in seconds to wait for an available context.

        Returns:
            AsyncBrowserContext: Playwright browser context.

        Raises:
            ScraperError: If no context is available within the timeout.
        """
        try:
            ctx = await asyncio.wait_for(self.queue.get(), timeout)
            logger.info("Acquired asynchronous browser context from pool")
            return ctx
        except asyncio.TimeoutError:
            raise ScraperError("No available asynchronous browser context in pool (timeout)")

    async def release_context(self, context: AsyncBrowserContext):
        """
        Release an async browser context back to the pool.

        Clears cookies and permissions before reuse.

        Args:
            context (AsyncBrowserContext): Context to release.
        """
        try:
            await context.clear_cookies()
            await context.clear_permissions()
            await self.queue.put(context)
            logger.info("Released asynchronous browser context back to pool")
        except Exception as e:
            logger.warning(f"Failed to release asynchronous context cleanly: {e}")
            try:
                await context.close()
            except Exception:
                pass

    async def close(self):
        """Shutdown the asynchronous browser pool and clean up resources."""
        logger.info("Closing asynchronous browser pool")
        try:
            while not self.queue.empty():
                ctx = await self.queue.get()
                try:
                    await ctx.close()
                except Exception:
                    pass
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.warning(f"Error during asynchronous pool cleanup: {e}")
