"""Negative API tests: missing/invalid auth and unknown resources are rejected cleanly."""
import requests

from conftest import REQUEST_TIMEOUT

# TODO: replace with real endpoints captured from the browser network tab.
LIST_ENDPOINT = "/TODO/list-projects-or-pipelines"
DETAIL_ENDPOINT = "/TODO/pipelines/{pipeline_id}"
NON_EXISTENT_ID = "00000000-0000-0000-0000-000000000000"  # TODO: match the real ID format (int vs UUID)
INVALID_TOKEN = "invalid.token.value"


def _assert_error_body(resp):
    # TODO: tighten once the real error shape is known (e.g. {"detail": "..."}).
    assert resp.text, "error response should have a body"
    if "application/json" in resp.headers.get("Content-Type", ""):
        body = resp.json()
        assert any(k in body for k in ("detail", "error", "message")), f"unexpected error body: {body}"


def test_no_auth_header_is_rejected(base_url, unauth_session):
    resp = unauth_session.get(f"{base_url}{LIST_ENDPOINT}", timeout=REQUEST_TIMEOUT)

    assert resp.status_code in (401, 403), f"{resp.status_code}: {resp.text}"
    _assert_error_body(resp)


def test_invalid_token_is_rejected(base_url):
    headers = {"Authorization": f"Bearer {INVALID_TOKEN}", "Accept": "application/json"}
    resp = requests.get(f"{base_url}{LIST_ENDPOINT}", headers=headers, timeout=REQUEST_TIMEOUT)

    assert resp.status_code in (401, 403), f"{resp.status_code}: {resp.text}"
    _assert_error_body(resp)


def test_non_existent_resource_returns_404(base_url, auth_session):
    url = f"{base_url}{DETAIL_ENDPOINT.format(pipeline_id=NON_EXISTENT_ID)}"
    resp = auth_session.get(url, timeout=REQUEST_TIMEOUT)

    # TODO: if the API returns something other than 404 (e.g. 403 or 200 with null),
    # document the actual behaviour here and in the README findings.
    assert resp.status_code == 404, f"{resp.status_code}: {resp.text}"
    _assert_error_body(resp)
