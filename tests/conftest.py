"""Shared test fixtures and env setup."""

import os

import pytest
from fastapi.testclient import TestClient


def pytest_configure(config: pytest.Config) -> None:
    os.environ.setdefault("ENVIRONMENT", "local")
    os.environ.setdefault("LOCAL_API_TOKEN", "test-token")


@pytest.fixture
def client() -> TestClient:
    from src.main import app

    return TestClient(app, headers={"Authorization": "Bearer test-token"})
