import os

import httpx


def test_openai_api_access_smoke() -> None:
    api_key = os.getenv("OMGENE_OPEN_AI_API_KEY")
    assert api_key, "OMGENE_OPEN_AI_API_KEY must be set to run this smoke test"

    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(timeout=10.0) as client:
        response = client.get("https://api.openai.com/v1/models", headers=headers)

    # print(response.text)

    assert response.status_code == 200, (
        "OpenAI API request failed; "
        f"status={response.status_code} body={response.text[:200]}"
    )
    payload = response.json()
    assert "data" in payload
