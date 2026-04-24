import asyncio
from models import User, Role, Permission, RolePermission
from auth.auth import register_user
from dbmanager import async_session

# since we are using alembic to manage migrations, ensure to migrate before running this script
# alembic upgrade head


async def seed_rbac():
    # Define permissions
    permission_defs = [
        {"name": "documents:create", "resource": "documents", "action": "create", "description": "Upload documents"},
        {"name": "documents:read", "resource": "documents", "action": "read", "description": "View documents"},
        {"name": "documents:update", "resource": "documents", "action": "update", "description": "Edit document metadata"},
        {"name": "documents:delete", "resource": "documents", "action": "delete", "description": "Delete documents"},
        {"name": "conversations:create", "resource": "conversations", "action": "create", "description": "Start conversations"},
        {"name": "conversations:read", "resource": "conversations", "action": "read", "description": "View conversations"},
        {"name": "conversations:update", "resource": "conversations", "action": "update", "description": "Edit conversations"},
        {"name": "conversations:delete", "resource": "conversations", "action": "delete", "description": "Delete conversations"},
        {"name": "users:read", "resource": "users", "action": "read", "description": "View user list"},
        {"name": "users:manage", "resource": "users", "action": "manage", "description": "Manage user accounts"},
        {"name": "roles:manage", "resource": "roles", "action": "manage", "description": "Manage roles and permissions"},
    ]

    # Upsert all permissions
    permissions_map = {}
    async with async_session() as session:
        for perm_def in permission_defs:
            perm = await Permission.objects.get(session=session, name=perm_def["name"])
            if not perm:
                perm = await Permission.objects.create(session=session, **perm_def)
            permissions_map[perm.name] = perm

        # Define roles with their permissions
        role_defs = [
            {
                "name": "admin",
                "description": "Full system access",
                "permissions": list(permissions_map.keys()),  # All permissions
            },
            {
                "name": "member",
                "description": "Standard user",
                "is_default": True,
                "permissions": [
                    "documents:create",
                    "documents:read",
                    "documents:update",
                    "documents:delete",
                    "conversations:create",
                    "conversations:read",
                    "conversations:update",
                    "conversations:delete",
                ],
            },
            {
                "name": "viewer",
                "description": "Read-only access",
                "permissions": ["documents:read", "conversations:read"],
            },
        ]

        for role_def in role_defs:
            role = await Role.objects.get(session=session, name=role_def["name"])
            if not role:
                role = await Role.objects.create(
                    session=session,
                    name=role_def["name"],
                    description=role_def["description"],
                    is_default=role_def.get("is_default", False),
                )
            
            # Link permissions to role
            for perm_name in role_def["permissions"]:
                perm = permissions_map[perm_name]
                # Check link
                link = await RolePermission.objects.get(session=session, role_id=role.id, permission_id=perm.id)
                if not link:
                    await RolePermission.objects.create(
                        session=session,
                        role_id=role.id,
                        permission_id=perm.id,
                    )
        
        await session.commit()
    
    print(f"RBAC seeded: {len(role_defs)} roles, {len(permission_defs)} permissions")


async def seed():
    # Clear existing data optionally or just upsert
    async with async_session() as session:
        # We use delete_all if we want a fresh start, otherwise we could just skip if count > 0
        await User.objects.delete_all(session=session)
        await RolePermission.objects.delete_all(session=session)
        await Role.objects.delete_all(session=session)
        await Permission.objects.delete_all(session=session)
        await session.commit()

    print("Cleared existing RBAC and User data")

    await seed_rbac()

    await register_user(
        email="admin@example.com",
        password="admin",
        tier="admin",
    )

    await register_user(
        email="user1@example.com",
        password="user1",
        tier="free",
    )

    await register_user(
        email="user2@example.com",
        password="user2",
        tier="free",
    )
    print("DB Seeded successfully")


if __name__ == "__main__":
    asyncio.run(seed())
