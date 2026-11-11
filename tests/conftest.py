"""Shared pytest configuration."""

import os

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip tests marked ``live`` (need Weaviate/Ollama) unless RUN_LIVE_TESTS=1."""
    if os.environ.get("RUN_LIVE_TESTS") == "1":
        return
    skip = pytest.mark.skip(reason="live test: set RUN_LIVE_TESTS=1 with Weaviate and Ollama running")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)
