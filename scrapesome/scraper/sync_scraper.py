"""
Synchronous Scraper Module for Scrapesome
-----------------------------------------

This module supports:
    - Single-URL synchronous scraping
    - Multi-URL concurrent scraping using threads
    - User-agent rotation
    - Optional HTTP redirect handling
    - Automatic fallback to Playwright rendering
    - Optional output formatting and file writing
"""

from typing import List, Optional, Union
import time
import requests
from requests.exceptions import RequestException
from concurrent.futures import ThreadPoolExecutor, as_completed

from scrapesome.logging import get_logger
from scrapesome.exceptions import ScraperError
from scrapesome.scraper.rendering import sync_render_page
from scrapesome.formatter.output_formatter import format_response
from scrapesome.utils.file_writer import write
from scrapesome.utils.browser_pool import SyncBrowserPool
from scrapesome.config import Settings

settings = Settings()
logger = get_logger()


def sync_scraper(
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
    save_to_file: Optional[bool] = False,
) -> Union[dict, List[dict]]:
    """
    Synchronous scraper supporting both single and multi-URL modes.

    Modes:
        • Single URL (default)
        • Multi-URL concurrent scraping if run_concurrently=True

    Args behave same as async_scraper except synchronous execution.
    """
    if urls:
        raise ScraperError("Parallel scraping is only supported in async_scraper().")

    if urls and url:
        raise ValueError("Provide only one of: url OR urls (not both).")

    if url is None and urls is None:
        raise ValueError("You must provide url or urls.")

    if timeout is None:
        timeout = int(settings.fetch_page_timeout)

    if not user_agents:
        user_agents = settings.default_user_agents

    if not output_format_type:
        output_format_type = settings.default_output_format

    if urls and len(urls)<2:
        pool_size=int(settings.browser_pool_size)

    if url and not run_concurrently:
        return _scrape_single(
            url=url,
            user_agents=user_agents,
            headers=headers,
            allow_redirects=allow_redirects,
            max_retries=max_retries,
            timeout=timeout,
            force_playwright=force_playwright,
            pool_size=1,
            output_format_type=output_format_type,
            file_name=file_name,
            save_to_file=save_to_file,
        )


    if urls and not run_concurrently:
        results = []
        for u in urls:
            r = _scrape_single(
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


    if urls and run_concurrently:

        if not pool_size:
            pool_size = settings.browser_pool_size

        logger.info(f"Running {len(urls)} URLs concurrently with pool_size={pool_size}")

        # Shared browser pool
        browser_pool = SyncBrowserPool(pool_size=pool_size)

        def worker(u):
            return _scrape_single(
                url=u,
                user_agents=user_agents,
                headers=headers,
                allow_redirects=allow_redirects,
                max_retries=max_retries,
                timeout=timeout,
                force_playwright=force_playwright,
                pool_size=browser_pool,
                output_format_type=output_format_type,
                file_name=None,
                save_to_file=save_to_file,
            )

        results = []
        with ThreadPoolExecutor(max_workers=pool_size) as executor:
            future_map = {executor.submit(worker, u): u for u in urls}

            for future in as_completed(future_map):
                results.append(future.result())

        browser_pool.close()
        return results



def _scrape_single(
    url: str,
    user_agents: List[str],
    headers: Optional[dict],
    allow_redirects: bool,
    max_retries: int,
    timeout: int,
    force_playwright: bool,
    pool_size: Optional[Union[int, SyncBrowserPool]],
    output_format_type: Optional[str],
    file_name: Optional[str],
    save_to_file: bool,
) -> dict:

    start = time.monotonic()

    try:
        content = fetch_url(
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
                file_name = url.replace("https://", "").replace("http://", "")
            file_name = write(data=content, file_name=file_name, output_format_type=output_format_type)

        end = time.monotonic()
        return {"data": content, "file": file_name, "time_taken": round(end - start, 4)}

    except Exception as e:
        end = time.monotonic()
        logger.exception(e)
        return {"error": str(e), "time_taken": round(end - start, 4)}

def fetch_url(
    url: str,
    user_agents: Optional[List[str]],
    headers: Optional[dict],
    allow_redirects: bool,
    max_retries: int,
    timeout: int,
    force_playwright: bool,
    pool_size: Optional[Union[int, SyncBrowserPool]],
) -> str:

    if user_agents is None:
        user_agents = settings.default_user_agents

    # Direct Playwright
    if force_playwright:
        return sync_render_page(url, timeout=timeout, pool=pool_size if isinstance(pool_size, SyncBrowserPool) else None)

    last_exception = None

    for attempt in range(max_retries):
        ua = user_agents[attempt % len(user_agents)]
        merged_headers = {"User-Agent": ua, **(headers or {})}

        try:
            response = requests.get(url, headers=merged_headers, allow_redirects=allow_redirects, timeout=timeout)
            status = response.status_code
            logger.info(f"Received response {status} for {url}")

            if status == 403:
                last_exception = ScraperError(f"403 Forbidden for URL {url}")
                time.sleep(1)
                continue

            response.raise_for_status()

            text = response.text

            if len(text.strip()) < 200:
                return sync_render_page(url, timeout=timeout, pool=pool_size if isinstance(pool_size, SyncBrowserPool) else None)

            return text

        except Exception as exc:
            last_exception = exc
            logger.error(f"Exception fetching {url}: {exc}")
            time.sleep(1)

    return sync_render_page(url, timeout=timeout, pool=pool_size if isinstance(pool_size, SyncBrowserPool) else None)
