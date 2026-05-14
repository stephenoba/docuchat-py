import pytest
from httpx import AsyncClient


async def get_auth_headers(client: AsyncClient, email: str = "doc_test@example.com"):
    payload = {"email": email, "password": "Password123!"}
    await client.post("/api/v1/auth/register", json=payload)

    login_params = {"email": email, "password": "Password123!"}
    token_response = await client.post("/api/v1/auth/token", params=login_params)
    access_token = token_response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.asyncio
async def test_create_document_success(client: AsyncClient):
    headers = await get_auth_headers(client)
    files = {"file": ("test.txt", b"This is a test content", "text/plain")}
    data = {"title": "Test Document"}
    response = await client.post("/api/v1/document", data=data, files=files, headers=headers)
    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    assert body["data"]["title"] == "Test Document"
    assert body["data"]["status"] == "pending"


@pytest.mark.asyncio
async def test_list_documents_success(client: AsyncClient):
    headers = await get_auth_headers(client, email="list@example.com")
    # Create two documents
    await client.post(
        "/api/v1/document", 
        data={"title": "Doc 1"}, 
        files={"file": ("doc1.txt", b"C1", "text/plain")}, 
        headers=headers
    )
    await client.post(
        "/api/v1/document", 
        data={"title": "Doc 2"}, 
        files={"file": ("doc2.txt", b"C2", "text/plain")}, 
        headers=headers
    )

    response = await client.get("/api/v1/document", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 2
    # Default sort is -created_at, so Doc 2 should be first
    assert body["data"][0]["title"] == "Doc 2"
    assert body["meta"]["total"] == 2
    assert body["meta"]["page"] == 1


@pytest.mark.asyncio
async def test_get_document_success(client: AsyncClient):
    headers = await get_auth_headers(client, email="get@example.com")
    create_resp = await client.post(
        "/api/v1/document",
        data={"title": "Target"},
        files={"file": ("target.txt", b"Find me", "text/plain")},
        headers=headers,
    )
    doc_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/document/{doc_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["title"] == "Target"


@pytest.mark.asyncio
async def test_update_document_success(client: AsyncClient):
    headers = await get_auth_headers(client, email="update@example.com")
    create_resp = await client.post(
        "/api/v1/document",
        data={"title": "Old Title"},
        files={"file": ("old.txt", b"Old Content", "text/plain")},
        headers=headers,
    )
    doc_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/document/{doc_id}", json={"title": "New Title"}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["title"] == "New Title"


@pytest.mark.asyncio
async def test_delete_document_soft(client: AsyncClient):
    headers = await get_auth_headers(client, email="delete@example.com")
    create_resp = await client.post(
        "/api/v1/document",
        data={"title": "To Delete"},
        files={"file": ("delete.txt", b"Bye", "text/plain")},
        headers=headers,
    )
    doc_id = create_resp.json()["data"]["id"]

    # Delete
    del_resp = await client.delete(f"/api/v1/document/{doc_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Verify it's gone from list
    list_resp = await client.get("/api/v1/document", headers=headers)
    assert len(list_resp.json()["data"]) == 0

    # Verify it's gone from GET by ID
    get_resp = await client.get(f"/api/v1/document/{doc_id}", headers=headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthorized_document_access(client: AsyncClient):
    # Try to access without token
    response = await client.get("/api/v1/document")
    assert response.status_code == 401
