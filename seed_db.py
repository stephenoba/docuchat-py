from models import User
from auth.auth import register_user
# since we are using alembic to manage migrations, ensure to migrate before running this script
# alembic upgrade head

if User.objects.delete_all():
    print("Deleted all users")

    user1 = register_user(
        email="admin@example.com",
        password="admin",
        tier="admin",
    )

    user2 = register_user(
        email="user1@example.com",
        password="user1",
        tier="free",
    )

    user3 = register_user(
        email="user2@example.com",
        password="user2",
        tier="free",
    )

else:
    print("Failed to delete all users")