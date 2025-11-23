# ScrapeSome

Welcome to the documentation for **ScrapeSome** — a modern, async/sync-capable web scraping library with smart fallbacks and HTML formatting.

![Scrapesome Logo](https://raw.githubusercontent.com/scrapesome/scrapesome/refs/heads/main/docs/assets/images/favicon.png)

**ScrapeSome** is a lightweight, flexible web scraping library with both **synchronous** and **asynchronous** support. It includes intelligent fallbacks, JavaScript page rendering, response formatting (HTML → Text/JSON/Markdown), and retry mechanisms. Ideal for developers who need robust scraping utilities with minimal setup.

---

## 💡 Why Use ScrapeSome?

- Handles both static and JS-heavy pages out of the box
- Supports both sync and async scraping
- Converts raw HTML into clean text, JSON, or Markdown
- Works with minimal configuration (`pip install scrapesome`)
- Handles timeouts, retries, redirects, user agents


## 🚀 Features

- 🔁 Sync + Async scraping support
- 🔄 Automatic retries and intelligent fallbacks
- 🧪 Playwright rendering fallback for JS-heavy pages
- ⚡ **Parallel scraping support (async-only)** — execute multiple requests simultaneously using shared Playwright browser pools.
- 📝 Format responses as raw HTML, plain **text**, **Markdown**, or structured **JSON**
- ⚙️ Configurable: timeouts, redirects, user agents, and logging
- 🧪 Test coverage with `pytest` and `pytest-asyncio`

---

## ⚖ Comparison with Alternatives

| Feature                          | ScrapeSome ✅                         | Playwright (Python)        | Selenium + UC               | Requests-HTML              | Scrapy + Playwright         |
|----------------------------------|--------------------------------------|-----------------------------|------------------------------|-----------------------------|------------------------------|
| 🧠 JS Rendering Support          | ✅ Auto fallback on 403/JS content    | ✅ Always (manual control)  | ✅ Always (manual control)   | ✅ Partial (via Pyppeteer)  | ✅ Requires setup            |
| 🔄 Automatic Fallback (403/Blank)| ✅ Yes (seamless)                     | ❌ Manual logic needed       | ❌ Manual logic needed        | ❌ No                       | ❌ Needs per-request config  |
| 🔁 Uses Browser Engine           | ✅ Only when needed (Playwright)      | ✅ Always                   | ✅ Always                    | ✅ (Unstable, slow)         | ✅ Always (if enabled)       |
| ✅ Sync + Async Support         | ✅ Built-in                           | ❌ Async only               | ❌ Manual (via threading)    | ❌ Sync only                | ❌ Async only (via plugin)   |
| 📝 JSON/Markdown/HTML Output    | ✅ Built-in formats                   | ❌ Manual parsing           | ❌ Manual parsing            | ❌ Basic only               | ❌ Custom pipeline needed    |
| ⚡ Minimal Setup                 | ✅ Near zero                          | ❌ Code + browser install   | ❌ Driver + setup            | ✅ Simple pip install       | ❌ Complex + plugin setup    |
| 🔁 Retries, Timeouts, Agents    | ✅ Smart defaults built-in            | ❌ Manual handling          | ❌ Manual handling           | ❌ Limited                  | ⚠️ Partial via settings      |
| 🧪 Pytest-Ready Out-of-the-box  | ✅ Fully testable                     | ⚠️ Requires mocks           | ❌ Hard to test              | ❌ Minimal                  | ⚠️ Needs testing harness     |
| ⚙️ Config via .env / Inline     | ✅ Flexible and optional              | ❌ Code/config only         | ❌ Manual via code           | ❌ Hardcoded mostly         | ⚠️ Project settings          |
| 📦 Install & Run in <1 Min      | ✅ Yes                                | ❌ Setup required           | ❌ Driver + config needed    | ✅ Yes                      | ❌ Needs project + plugin    |



## 📦 Installation

```bash
pip install scrapesome
```

## 🧪 Testing
Run tests with:

```bash
pytest --cov=scrapesome tests/
```
Target coverage: 75–100%

## 📁 Project Structure

```text
scrapesome/
├── .gitignore
├── pytest.ini
├── mkdocs.yml
├── .github/
│   ├── workflows/
│   │   └── deploy.yml
│   ├── ISSUE_TEMPLATE/
│   │   └── index.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── CODE_OF_CONDUCT.md
│   └── SECURITY.md
├── __init__.py
├── cli.py
├── config.py
├── exceptions.py
├── formatter/
│   ├── __init__.py
│   └── output_formatter.py
├── logging.py
├── scraper/
│   ├── __init__.py
│   ├── async_scraper.py
│   ├── sync_scraper.py
│   └── rendering.py
├── utils/
│   ├── __init__.py
│   ├── browser_pool.py
│   └── file_writer.py
├── docs/
│   ├── index.md
│   ├── getting_started.md
│   ├── usage.md
│   ├── config.md
│   ├── examples.md
│   ├── cli.md
│   ├── about.md
│   ├── licence.md
│   ├── file-saving.md
│   ├── contribution.md
│   ├── output-formats.md
│   └── assets/
│       └── images/
│           └── favicon.png
├── tests/
│   ├── __init__.py
│   ├── test_sync_scraper.py
│   ├── test_async_scraper.py
│   ├── test_config.py
│   ├── test_logging.py
│   ├── test_rendering.py
│   ├── test_file_writer.py
│   ├── test_output_formatter.py
│   └── test_cli.py
├── setup.py
├── requirements.txt
├── pyproject.toml
├── LICENSE
└── README.md
```

## 🔒 License
MIT License © 2025