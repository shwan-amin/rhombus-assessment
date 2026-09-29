"""Shared fixtures for Rhombus AI API tests.

Values come from ../.env (copy .env.example). Tests are skipped, not failed,
when the required variables are missing.
"""
import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

REQUEST_TIMEOUT = 30  # seconds


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        pytest.skip(f"{name} is not set in .env - see .env.example (value comes from the browser network tab)")
    return value


@pytest.fixture(scope="session")
def base_url() -> str:
    return _require_env("RHOMBUS_API_BASE_URL").rstrip("/")


@pytest.fixture(scope="session")
def auth_headers() -> dict:
    token = _require_env("RHOMBUS_AUTH_TOKEN")
    # TODO: confirm the auth scheme from the network tab (Bearer header vs cookie vs custom header).
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


@pytest.fixture
def auth_session(auth_headers) -> requests.Session:
    session = requests.Session()
    session.headers.update(auth_headers)
    yield session
    session.close()


@pytest.fixture
def unauth_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    yield session
    session.close()
