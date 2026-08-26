"""Integration checks against deployed endpoints.

These tests are environment-aware and skip when endpoint vars are not provided.
"""

from __future__ import annotations

import os

import pytest
import requests


PIZZA_API_URL = os.getenv("PIZZA_API_URL")
REGISTRATION_API_URL = os.getenv("REGISTRATION_API_URL")


@pytest.mark.integration
@pytest.mark.skipif(not PIZZA_API_URL, reason="PIZZA_API_URL not configured")
def test_pizza_api_reachable() -> None:
    response = requests.get(PIZZA_API_URL.rstrip("/"), timeout=15)
    assert response.status_code < 500


@pytest.mark.integration
@pytest.mark.skipif(not REGISTRATION_API_URL, reason="REGISTRATION_API_URL not configured")
def test_registration_api_reachable() -> None:
    response = requests.get(REGISTRATION_API_URL.rstrip("/"), timeout=15)
    assert response.status_code < 500
