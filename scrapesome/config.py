"""
Environment configuration loader for the Scrapesome application.

This module defines a `Settings` class that loads all required environment
variables at startup and makes them available as attributes.

Raises:
    EnvironmentError: If a required environment variable is missing.
"""

import os
from typing import Any

class Settings:
    """
    Loads and stores all required environment variables for the application.
    """

    def __init__(self) -> None:
        # APP Configuration
        self.log_level = self._get("LOG_LEVEL", default="INFO")

        #⚙️ Scraper Behavior Settings
        self.max_workers = self._get("MAX_WORKERS", default="1")

        #📤 Output Format Defaults
        self.default_output_format = self._get("OUTPUT_FORMAT", default="html")

        #📁 Supported File Extensions
        self.file_extensions = self._get("FILE_EXTENSIONS", default={
        'json': '.json',
        'markdown': '.md',
        'text': '.txt',
        'html': '.html'
        })

        

        self.fetch_playwright_timeout = self._get("FETCH_PLAYWRIGHT_TIMEOUT", default="60000")
        self.fetch_page_timeout = self._get("FETCH_PAGE_TIMEOUT", default="60000")
        self.default_user_agents = self._get("USER_AGENTS", default=[
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0",
        ])
        self.browser_pool_size = self._get("PLAYWRIGHT_BROWSER_POOL_SIZE", default="1")


    def _get(self, key: str, default: Any | None = None):
        """
        Retrieve an environment variable, or raise an error if missing and no default is provided.

        Args:
            key (str): The name of the environment variable.
            default (Optional[str]): Default value if the variable is not set.

        Returns:
            any: The value of the environment variable.

        Raises:
            EnvironmentError: If the variable is not set and no default is provided.
        """
        value = os.getenv(key)
        if value is None:
            if default is not None:
                # logging.warning("[Config] Environment variable '%s' not set, using default: '%s'", key, default)
                return default
            raise EnvironmentError(f"Missing required environment variable: '{key}'")
        return value
