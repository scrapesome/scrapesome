# Scrapesome — Parallel & Standard Scraping Guide

Scrapesome provides flexible, high-performance scraping with support for both standard HTTP requests and JavaScript-rendered pages via Playwright.

## Key Features

- HTTP fetching (sync and async modes)  
- Automatic retry handling  
- User-agent rotation  
- Configurable redirect handling  
- JavaScript rendering via Playwright  
- Optional output formatting (text, markdown, JSON)  
- Optional file saving  
- **Parallel scraping support (async only)**

## Parallel Scraping (Asynchronous Only)

Parallel scraping is available **only** via `async_scraper()`.

Parallelism uses:

- Python `asyncio` for concurrency  
- A shared Playwright browser/context pool  
- Semaphores to limit simultaneous page operations

**Supported**  
(Example usage shown as an indented code block)

    async_scraper(urls=[...], run_concurrently=True, pool_size=N)

**Not Supported**

- Parallel execution using `sync_scraper`  
- Thread-based parallelism with the synchronous Playwright API

If parallel mode is attempted with the synchronous scraper, raise a clear error:

    Parallel scraping is only supported in async_scraper().
    Use async_scraper(..., run_concurrently=True) instead.


## Usage Examples

Below are examples for asynchronous workflows. Code examples are presented as indented blocks to avoid nested fence collisions.

### Asynchronous Scraper (Supports Parallel Scraping)

**Basic Async Fetch**

    import asyncio
    from scrapesome import async_scraper

    async def run():
        result = await async_scraper("https://example.com")
        print(result)

    asyncio.run(run())

**Force JavaScript Rendering**

    import asyncio
    from scrapesome import async_scraper

    async def run():
        result = await async_scraper(
            "https://example.com",
            force_playwright=True
        )
        print(result)

    asyncio.run(run())

**Parallel Scraping (Async Only)**

    import asyncio
    from scrapesome import async_scraper

    urls = [
        "https://www.wikipedia.org",
        "https://httpbin.org/html",
        "https://example.com"
    ]

    async def run_parallel():
        results = await async_scraper(
            urls=urls,
            run_concurrently=True,
            pool_size=3,          # number of parallel tasks/browser contexts
            force_playwright=True,
            save_to_file=True
        )

        for u, r in zip(urls, results):
            print(f"{u} → {r.get('time_taken')}s")

    asyncio.run(run_parallel())

**Custom Headers and User Agents**

    import asyncio
    from scrapesome import async_scraper

    async def run():
        result = await async_scraper(
            "https://example.com",
            user_agents=["AgentX/1.0"],
            headers={"X-Debug": "1"}
        )
        print(result)

    asyncio.run(run())

## File Output

File saving is supported in both sync and async scrapers.

    from scrapesome import async_scraper

    await async_scraper(
        "https://example.com",
        output_format_type="markdown",
        save_to_file=True
    )

A file will be created with an auto-derived name based on the URL.

## Feature Comparison

| Feature                | sync_scraper | async_scraper |
|------------------------|--------------|---------------|
| HTTP scraping          | Yes          | Yes           |
| User-agent rotation    | Yes          | Yes           |
| JS rendering           | Yes          | Yes           |
| Output formatting      | Yes          | Yes           |
| File saving            | Yes          | Yes           |
| Parallel scraping      | No           | Yes           |

## Notes

- Use `async_scraper` when performance or concurrency is required.  
- Use `sync_scraper` for simpler single-URL workflows.  
- Playwright concurrency is supported safely in the asynchronous API only.
