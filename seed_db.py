from models.models import User
# since we are using alembic to manage migrations, ensure to migrate before running this script
# alembic upgrade head

if User.objects.delete_all():
    print("Deleted all users")

    user1 = User.objects.create(
        username="admin",
        email="admin@example.com",
        password_hash="admin",
        tier="admin",
        tokens_used=0,
    )

    user2 = User.objects.create(
        username="user1",
        email="user1@example.com",
        password_hash="user1",
        tier="free",
        tokens_used=0,
    )

    user3 = User.objects.create(
        username="user2",
        email="user2@example.com",
        password_hash="user2",
        tier="free",
        tokens_used=0,
    )

else:
    print("Failed to delete all users")