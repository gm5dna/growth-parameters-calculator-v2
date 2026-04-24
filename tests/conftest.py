"""Shared pytest fixtures."""
import pytest
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def app():
    """Create Flask application for testing."""
    from app import app as flask_app, limiter
    flask_app.config["TESTING"] = True
    flask_app.config["RATELIMIT_ENABLED"] = False
    # The RATELIMIT_ENABLED flag is checked at request time for future
    # decorators, but already-registered in-memory counters can persist
    # across tests; reset them each fixture construction to keep the
    # PDF-heavy integration tests from tripping a 429.
    limiter.enabled = False
    try:
        limiter.reset()
    except Exception:
        pass
    yield flask_app
    limiter.enabled = True


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()
