"""
ScrapeSome Library
==================

Main entry point for the ScrapeSome scraping library.

"""
from .scraper.sync_scraper import sync_scraper
from .scraper.async_scraper import async_scraper

__all__ = ["sync_scraper", "async_scraper"]

__version__ = "0.1.7"
