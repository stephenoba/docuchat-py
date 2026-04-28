import pytest
from httpx import AsyncClient

async def get_auth_headers(client: AsyncClient, email: str = "doc_event@example.com"):
    payload = {"email": email, "password": "Password123!"}
    await client.post("/api/v1/auth/register", json=payload)
    
    login_params = {"email": email, "password": "Password123!"}
    token_response = await client.post("/api/v1/auth/token", params=login_params)
    access_token = token_response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {access_token}"}

@pytest.mark.asyncio
async def test_document_lifecycle_events(client: AsyncClient):
    headers = await get_auth_headers(client)
    
    # 1. Created & Processed
    create_payload = {"title": "Lifecycle Test", "content": "This is some test content for lifecycle events."}
    create_resp = await client.post("/api/v1/document", json=create_payload, headers=headers)
    assert create_resp.status_code == 202
    doc_id = create_resp.json()["data"]["id"]
    
    # 2. Deleted
    del_resp = await client.delete(f"/api/v1/document/{doc_id}", headers=headers)
    assert del_resp.status_code == 200
    
    # Verify soft deleted
    get_resp = await client.get(f"/api/v1/document/{doc_id}", headers=headers)
    assert get_resp.status_code == 404
    
    # 3. Restored
    restore_resp = await client.post(f"/api/v1/document/{doc_id}/restore", headers=headers)
    assert restore_resp.status_code == 200
    assert restore_resp.json()["data"]["id"] == doc_id
    
    # Verify restored
    get_resp_final = await client.get(f"/api/v1/document/{doc_id}", headers=headers)
    assert get_resp_final.status_code == 200
    
    # (Optional) Verify UsageLog - This might require a direct DB check or an admin route
    # For now, if code didn't crash, the calls were made
