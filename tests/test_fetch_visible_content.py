"""Unit tests for the `scrapesome.utils.fetch_visible_content` utility."""

from scrapesome.utils.fetch_visible_content import visible_text_length


def test_visible_text_length_counts_visible_chars():
    html = """
    <html>
        <head><title>Title</title></head>
        <body>
            <h1>Hello World</h1>
            <p>This is visible text.</p>
        </body>
    </html>
    """

    assert len(visible_text_length(html)) == len("Hello World This is visible text.")


def test_visible_text_length_ignores_non_visible_elements():
    html = """
    <html>
        <body>
            <script>console.log('hidden')</script>
            <style>body { display: none; }</style>
            <noscript>Unavailable</noscript>
            <meta charset=\"utf-8\" />
            <div>Visible</div>
        </body>
    </html>
    """

    assert len(visible_text_length(html)) == len("Visible")


def test_visible_text_length_returns_zero_for_empty_html():
    assert len(visible_text_length("")) == 0
