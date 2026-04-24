"""Shared pytest fixtures."""
import pytest

# Project root is added to sys.path via pyproject.toml `tool.pytest.ini_options`;
# see `pythonpath = ["."]` there. No runtime sys.path mutation is needed.


@pytest.fixture
def app():
    """Create Flask application for testing."""
    from app import app as flask_app
    from app import limiter
    flask_app.config["TESTING"] = True
    flask_app.config["RATELIMIT_ENABLED"] = False
    # The RATELIMIT_ENABLED flag is checked at request time for future
    # decorators, but already-registered in-memory counters can persist
    # across tests; reset them each fixture construction to keep the
    # PDF-heavy integration tests from tripping a 429.
    limiter.enabled = False
    try:
        limiter.reset()
        yield flask_app
    finally:
        limiter.enabled = True


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()
