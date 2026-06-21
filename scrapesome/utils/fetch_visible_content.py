"""Utilities for extracting visible text from HTML content."""

from bs4 import BeautifulSoup

def visible_text_length(html: str) -> int:
    """Return the length of the visible text in an HTML document.

    Args:
        html: A string containing the HTML markup to analyze.

    Returns:
        The number of visible characters found in the HTML content.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove non-visible elements
    for tag in soup(["script", "style", "noscript", "meta", "head"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    return text