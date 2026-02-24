import asyncio

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import hash_password


USERS = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "operator", "password": "operator123", "role": "operator"},
    {"username": "viewer", "password": "viewer123", "role": "viewer"},
]


async def main():
    async with AsyncSessionLocal() as db:
        for u in USERS:
            result = await db.execute(
                User.__table__.select().where(User.username == u["username"])
            )
            if result.first():
                continue

            db.add(
                User(
                    username=u["username"],
                    password_hash=hash_password(u["password"]),
                    role=u["role"],
                    is_active=True,
                )
            )

        await db.commit()

    print("✅ Users ensured: admin / operator / viewer")


if __name__ == "__main__":
    asyncio.run(main())
