"""Positive API tests: authenticated requests return the expected data."""
from conftest import REQUEST_TIMEOUT

# TODO: replace with real endpoints captured from the browser network tab.
LIST_ENDPOINT = "/TODO/list-projects-or-pipelines"
DETAIL_ENDPOINT = "/TODO/pipelines/{pipeline_id}"
# TODO: ID of the pipeline built for this assessment.
KNOWN_PIPELINE_ID = "TODO_PIPELINE_ID"


def test_list_pipelines_returns_items(base_url, auth_session):
    resp = auth_session.get(f"{base_url}{LIST_ENDPOINT}", timeout=REQUEST_TIMEOUT)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # TODO: adjust to the real response shape (e.g. body["results"] / body["data"]).
    items = body if isinstance(body, list) else body.get("TODO_ITEMS_KEY", [])
    assert isinstance(items, list) and items, f"expected a non-empty list, got: {body}"
    assert all("TODO_ID_FIELD" in item for item in items)
    assert any(str(item.get("TODO_ID_FIELD")) == KNOWN_PIPELINE_ID for item in items), \
        "the assessment pipeline should be listed"


def test_get_pipeline_details(base_url, auth_session):
    url = f"{base_url}{DETAIL_ENDPOINT.format(pipeline_id=KNOWN_PIPELINE_ID)}"
    resp = auth_session.get(url, timeout=REQUEST_TIMEOUT)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # TODO: adjust field names to the real response.
    assert str(body["TODO_ID_FIELD"]) == KNOWN_PIPELINE_ID
    assert body["TODO_NAME_FIELD"], "pipeline should have a name"
    # e.g. the pipeline should reference an S3 source and a GCS destination:
    # assert body["source"]["type"] == "s3"
    # assert body["destination"]["type"] == "gcs"
