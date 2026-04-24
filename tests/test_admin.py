import pytest
from httpx import AsyncClient
import uuid

async def get_admin_headers(client: AsyncClient):
    # Register an admin
    email = f"admin_{uuid.uuid4().hex[:6]}@example.com"
    payload = {"email": email, "password": "Password123!", "tier": "admin", "roles": ["admin"]}
    await client.post("/api/v1/auth/register", json=payload)
    
    # Login
    login_resp = await client.post(f"/api/v1/auth/token?email={email}&password=Password123!")
    token = login_resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

async def get_user_headers(client: AsyncClient):
    # Register a standard user
    email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    payload = {"email": email, "password": "Password123!"}
    await client.post("/api/v1/auth/register", json=payload)
    
    # Login
    login_resp = await client.post(f"/api/v1/auth/token?email={email}&password=Password123!")
    token = login_resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, email

@pytest.mark.asyncio
async def test_list_roles_success(client: AsyncClient):
    headers = await get_admin_headers(client)
    response = await client.get("/api/v1/admin/roles", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) > 0
    # Check if admin role is present
    role_names = [role["name"] for role in data]
    assert "admin" in role_names
    assert "member" in role_names

@pytest.mark.asyncio
async def test_admin_routes_forbidden_for_member(client: AsyncClient):
    headers, _ = await get_user_headers(client)
    response = await client.get("/api/v1/admin/roles", headers=headers)
    assert response.status_code == 403
    assert "Missing required permission" in response.json()["error"]["message"]

@pytest.mark.asyncio
async def test_assign_and_revoke_role(client: AsyncClient):
    admin_headers = await get_admin_headers(client)
    user_headers, user_email = await get_user_headers(client)
    
    # Get user ID
    me_resp = await client.get("/api/v1/user/me", headers=user_headers)
    user_id = me_resp.json()["data"]["id"]
    
    # Assign role
    assign_resp = await client.post(
        f"/api/v1/admin/users/{user_id}/roles",
        headers=admin_headers,
        json={"role_name": "viewer"}
    )
    assert assign_resp.status_code == 200
    
    # Verify role is assigned
    me_resp_after = await client.get("/api/v1/user/me", headers=user_headers)
    assert "viewer" in me_resp_after.json()["data"]["roles"]
    
    # Revoke role
    revoke_resp = await client.delete(
        f"/api/v1/admin/users/{user_id}/roles/viewer",
        headers=admin_headers
    )
    assert revoke_resp.status_code == 200
    
    # Verify role is revoked
    me_resp_final = await client.get("/api/v1/user/me", headers=user_headers)
    assert "viewer" not in me_resp_final.json()["data"]["roles"]
