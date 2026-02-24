import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.user import User


async def main():
    async with AsyncSessionLocal() as db:
        # выставляем роли как надо
        mapping = {
            "admin": "admin",
            "operator": "operator",
            "viewer": "viewer",
        }

        res = await db.execute(select(User))
        users = res.scalars().all()

        for u in users:
            if u.username in mapping:
                u.role = mapping[u.username]
                u.is_active = True

        await db.commit()

    print("✅ Roles fixed: admin/admin, operator/operator, viewer/viewer")


if __name__ == "__main__":
    asyncio.run(main())
