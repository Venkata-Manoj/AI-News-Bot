"""pytest configuration for AI News Bot tests."""
import os
import sys

# Add project root to sys.path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "network: mark test as requiring network access")
    config.addinivalue_line(
        "markers", "youtube: mark test as requiring YouTube API key"
    )
