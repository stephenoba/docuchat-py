import asyncio
from models import User
from auth.auth import register_user

# since we are using alembic to manage migrations, ensure to migrate before running this script
# alembic upgrade head

async def seed():
    if await User.objects.delete_all():
        print("Deleted all users")

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
    else:
        print("Failed to delete all users")

if __name__ == "__main__":
    asyncio.run(seed())