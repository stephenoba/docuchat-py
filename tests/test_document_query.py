import pytest
from httpx import AsyncClient

async def get_auth_headers(client: AsyncClient, email: str = "query@example.com"):
    payload = {"email": email, "password": "Password123!"}
    await client.post("/api/v1/auth/register", json=payload)
    login_params = {"email": email, "password": "Password123!"}
    token_response = await client.post("/api/v1/auth/token", params=login_params)
    access_token = token_response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {access_token}"}

@pytest.mark.asyncio
async def test_list_documents_filtering_and_sorting(client: AsyncClient):
    headers = await get_auth_headers(client)
    
    # Create test documents
    docs = [
        {"title": "Banana", "content": "Yellow fruit", "filename": "b.txt"},
        {"title": "Apple", "content": "Red fruit", "filename": "a.txt"},
        {"title": "Cherry", "content": "Small fruit", "filename": "c.txt"},
    ]
    for doc in docs:
        await client.post("/api/v1/document", json=doc, headers=headers)

    # 1. Test search
    resp = await client.get("/api/v1/document?search=apple", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert len(data) == 1
    assert data[0]["title"] == "Apple"
    assert body["meta"]["total"] == 1

    # 2. Test sorting asc
    resp = await client.get("/api/v1/document?sort=title", headers=headers)
    data = resp.json()["data"]
    titles = [d["title"] for d in data]
    assert titles == ["Apple", "Banana", "Cherry"]

    # 3. Test sorting desc
    resp = await client.get("/api/v1/document?sort=-title", headers=headers)
    data = resp.json()["data"]
    titles = [d["title"] for d in data]
    assert titles == ["Cherry", "Banana", "Apple"]

    # 4. Filter by status (simulated as 'pending' in creation)
    resp = await client.get("/api/v1/document?status=pending", headers=headers)
    assert len(resp.json()["data"]) == 3
    
    resp = await client.get("/api/v1/document?status=ready", headers=headers)
    assert len(resp.json()["data"]) == 0
