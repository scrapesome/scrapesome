"""
test_file_writer.py

Unit tests for the `write` function in the `file_writer` module.

Tests cover:
- Writing JSON data to a file.
- Writing plain text data to a file.
- Handling unsupported file format by raising ValueError.

Uses pytest and pytest-mock for mocking dependencies.
"""

import builtins
import json
from unittest.mock import Mock, mock_open

import pytest
from scrapesome.utils.file_writer import write


@pytest.fixture
def mock_extensions():
    """
    Fixture to provide mock file extensions mapping.
    """
    return {
        'json': '.json',
        'markdown': '.md',
        'text': '.txt',
        'html': '.html'
    }


def test_write_json(monkeypatch, mock_extensions):
    """
    Test that `write` correctly writes JSON data to a file,
    uses the proper file extension, calls the logger info once,
    and opens the file with correct parameters.
    """
    mock_settings = Mock()
    mock_settings.file_extensions = mock_extensions
    monkeypatch.setattr('scrapesome.utils.file_writer.settings', mock_settings)

    mock_file = mock_open()
    monkeypatch.setattr(builtins, 'open', mock_file, raising=False)

    mock_logger = Mock()
    monkeypatch.setattr('scrapesome.utils.file_writer.logger', mock_logger)

    data = {"key": "value"}
    file_name = "test_output"
    output_format_type = "json"

    result = write(data, file_name, output_format_type)

    assert result == "test_output.json"
    mock_file.assert_called_once_with("test_output.json", 'w', encoding='utf-8')
    mock_logger.info.assert_called_once()
    assert "writing scraped data into file test_output.json completed." in mock_logger.info.call_args[0][0]


def test_write_text(monkeypatch, mock_extensions):
    """
    Test that `write` correctly writes plain text data to a file,
    uses the proper file extension, writes the exact data content,
    calls the logger info once, and opens the file correctly.
    """
    mock_settings = Mock()
    mock_settings.file_extensions = mock_extensions
    monkeypatch.setattr('scrapesome.utils.file_writer.settings', mock_settings)

    mock_file = mock_open()
    monkeypatch.setattr(builtins, 'open', mock_file, raising=False)

    mock_logger = Mock()
    monkeypatch.setattr('scrapesome.utils.file_writer.logger', mock_logger)

    data = "Hello, pytest!"
    file_name = "readme"
    output_format_type = "text"

    result = write(data, file_name, output_format_type)

    assert result == "readme.txt"
    mock_file.assert_called_once_with("readme.txt", 'w', encoding='utf-8')
    handle = mock_file()
    handle.write.assert_called_once_with(data)

    mock_logger.info.assert_called_once()
    assert "writing scraped data into file readme.txt completed." in mock_logger.info.call_args[0][0]


def test_write_unsupported_format_raises(monkeypatch, mock_extensions):
    """
    Test that `write` raises a ValueError when called with an unsupported format.
    """
    mock_settings = Mock()
    mock_settings.file_extensions = mock_extensions
    monkeypatch.setattr('scrapesome.utils.file_writer.settings', mock_settings)

    data = "data"
    file_name = "file"
    output_format_type = "xml"  # unsupported format

    with pytest.raises(ValueError) as excinfo:
        write(data, file_name, output_format_type)

    assert "Unsupported format" in str(excinfo.value)