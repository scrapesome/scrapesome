"""
Asynchronous Scraper Module for Scrapesome
------------------------------------------

This module provides both single-URL and multi-URL asynchronous scraping with:

    - User-agent rotation
    - Optional HTTP redirect following
    - Automatic fallback to Playwright JS rendering
    - Optional concurrency (parallel fetching)
    - Integration with Browser Pool
    - Output formatting + optional file saving

Usage (single URL):
    await async_scraper("https://example.com")

Usage (multiple URLs, parallel):
    await async_scraper(
        urls=["a.com", "b.com", "c.com"],
        run_concurrently=True,
        pool_size=3
    )
"""

from typing import List, Optional, Union
import asyncio
import httpx
from scrapesome.logging import get_logger
from scrapesome.exceptions import ScraperError
from scrapesome.scraper.rendering import async_render_page
from scrapesome.formatter.output_formatter import format_response
from scrapesome.utils.file_writer import write
from scrapesome.utils.browser_pool import AsyncBrowserPool
from scrapesome.config import Settings

settings = Settings()
logger = get_logger()


async def async_scraper(
    url: Optional[str] = None,
    urls: Optional[List[str]] = None,
    run_concurrently: bool = False,
    pool_size: Optional[int] = None,
    user_agents: Optional[List[str]] = None,
    headers: Optional[dict] = None,
    allow_redirects: bool = True,
    max_retries: int = 3,
    timeout: int = None,
    force_playwright: bool = False,
    output_format_type: Optional[str] = None,
    file_name: Optional[str] = None,
    save_to_file: Optional[bool] = False
) -> Union[dict, List[dict]]:
    """
    Main entrypoint for async scraping.

    Supports:
        1) Single URL scraping
        2) Multi-URL concurrent scraping via run_concurrently=True

    Args:
        url (str): Single URL mode.
        urls (List[str]): Multi-URL mode.
        run_concurrently (bool): Enables concurrency when urls list is provided.
        pool_size (int): Max parallel requests + matching browser pool size.
        user_agents, headers, allow_redirects, max_retries, timeout, force_playwright:
            Same behavior as before.
        output_format_type: Format final response.
        save_to_file: Whether to save output to a file.

    Returns:
        dict for single URL
        List[dict] for multiple URLs
    """

    # --------------------------------------------------------
    # 1 — Decide if SINGLE or MULTIPLE URL mode
    # --------------------------------------------------------

    if urls and not isinstance(urls, list):
        raise ValueError("urls must be a list of strings.")

    if urls and url:
        raise ValueError("Provide only one of: url OR urls (not both).")

    # Normalize default timeout
    if timeout is None:
        timeout = int(settings.fetch_page_timeout)

    # Normalize user-agents
    if not user_agents:
        user_agents = settings.default_user_agents

    # Normalize output format
    if not output_format_type:
        output_format_type = settings.default_output_format

    if urls and len(urls)<2:
        pool_size=int(settings.browser_pool_size)

    if url and not run_concurrently:
        return await _scrape_single(
            url=url,
            user_agents=user_agents,
            headers=headers,
            allow_redirects=allow_redirects,
            max_retries=max_retries,
            timeout=timeout,
            force_playwright=force_playwright,
            pool_size=1,                     # IGNORE pool_size for single URL
            output_format_type=output_format_type,
            file_name=file_name,
            save_to_file=save_to_file,
        )

    if urls:

        # If concurrency OFF → do one by one (sequential)
        if not run_concurrently:
            results = []
            for u in urls:
                r = await _scrape_single(
                    url=u,
                    user_agents=user_agents,
                    headers=headers,
                    allow_redirects=allow_redirects,
                    max_retries=max_retries,
                    timeout=timeout,
                    force_playwright=force_playwright,
                    pool_size=1,
                    output_format_type=output_format_type,
                    file_name=None,
                    save_to_file=save_to_file,
                )
                results.append(r)
            return results

        if not pool_size:
            pool_size = settings.browser_pool_size

        logger.info(f"Running {len(urls)} URLs concurrently with pool_size={pool_size}")

        semaphore = asyncio.Semaphore(pool_size)
        browser_pool = await AsyncBrowserPool.create(pool_size=pool_size)

        async def worker(u):
            async with semaphore:
                return await _scrape_single(
                    url=u,
                    user_agents=user_agents,
                    headers=headers,
                    allow_redirects=allow_redirects,
                    max_retries=max_retries,
                    timeout=timeout,
                    force_playwright=force_playwright,
                    pool_size=browser_pool,     # <— pass browser pool instance
                    output_format_type=output_format_type,
                    file_name=None,
                    save_to_file=save_to_file,
                )

        try:
            results = await asyncio.gather(*(worker(u) for u in urls))
        finally:
            await browser_pool.close()

        return results

    # Nothing provided
    raise ValueError("You must provide either `url` or `urls`.")

async def _scrape_single(
    url: str,
    user_agents: List[str],
    headers: Optional[dict],
    allow_redirects: bool,
    max_retries: int,
    timeout: int,
    force_playwright: bool,
    pool_size: Optional[Union[int, AsyncBrowserPool]],
    output_format_type: Optional[str],
    file_name: Optional[str],
    save_to_file: bool
) -> dict:

    start = asyncio.get_event_loop().time()

    try:
        content = await fetch_url(
            url=url,
            user_agents=user_agents,
            headers=headers,
            allow_redirects=allow_redirects,
            max_retries=max_retries,
            timeout=timeout,
            force_playwright=force_playwright,
            pool_size=pool_size,
        )

        if output_format_type:
            content = format_response(html=content, url=url, output_format_type=output_format_type)

        if save_to_file:
            if not file_name:
                file_name = url.replace("https://", "").replace("http://", "").replace("/","_")
            file_name = write(data=content, file_name=file_name, output_format_type=output_format_type)

        end = asyncio.get_event_loop().time()
        return {"data": content, "file": file_name, "time_taken": round(end - start, 4)}

    except Exception as e:
        end = asyncio.get_event_loop().time()
        logger.exception(e)
        return {"error": str(e), "time_taken": round(end - start, 4)}

async def fetch_url(
    url: str,
    user_agents: Optional[List[str]],
    headers: Optional[dict],
    allow_redirects: bool,
    max_retries: int,
    timeout: Optional[int],
    force_playwright: bool,
    pool_size: Optional[Union[int, AsyncBrowserPool]] = None,
) -> str:

    if user_agents is None:
        user_agents = settings.default_user_agents

    if timeout is None:
        timeout = int(settings.fetch_page_timeout)

    # If force playwright → skip HTTP
    if force_playwright:
        logger.info(f"Force Playwright rendering enabled for URL: {url}")
        pool_arg = pool_size if isinstance(pool_size, AsyncBrowserPool) else None
        return await async_render_page(url, timeout=timeout, pool=pool_arg)

    last_exception = None

    for attempt in range(max_retries):
        ua = user_agents[attempt % len(user_agents)]
        ua_header = {"User-Agent": ua}
        merged_headers = {**ua_header, **(headers or {})}

        logger.info(f"Attempt {attempt+1}/{max_retries} fetching {url}")

        try:
            async with httpx.AsyncClient(
                follow_redirects=allow_redirects,
                timeout=timeout
            ) as client:

                response = await client.get(url, headers=merged_headers)
                status = response.status_code
                logger.info(f"Received response {status} for {url}")

                if status == 403:
                    last_exception = ScraperError(f"403 Forbidden for {url}")
                    await asyncio.sleep(1)
                    continue

                response.raise_for_status()
                text = response.text

                if len(text.strip()) < 200:
                    logger.info(f"Content too short → trying JS rendering for {url}")

                    pool_arg = pool_size if isinstance(pool_size, AsyncBrowserPool) else None
                    return await async_render_page(url, timeout=timeout, pool=pool_arg)

                return text

        except Exception as exc:
            last_exception = exc
            logger.error(f"RequestException for {url} on attempt {attempt+1}: {exc}")
            await asyncio.sleep(1)

    # Fallback after retries
    pool_arg = pool_size if isinstance(pool_size, AsyncBrowserPool) else None
    return await async_render_page(url, timeout=timeout, pool=pool_arg)
