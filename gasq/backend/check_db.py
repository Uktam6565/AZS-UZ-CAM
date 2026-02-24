import asyncio
from sqlalchemy import text

from app.db.engine import engine


async def main():
    async with engine.begin() as conn:
        db = (await conn.execute(text("select current_database()"))).scalar()
        schema = (await conn.execute(text("select current_schema()"))).scalar()
        stations = (await conn.execute(text("select to_regclass('public.stations')"))).scalar()
        print("DB:", db)
        print("schema:", schema)
        print("public.stations:", stations)

        # бонус: список таблиц
        rows = (await conn.execute(text("""
            select table_name
            from information_schema.tables
            where table_schema='public'
            order by table_name
        """))).all()
        print("tables:", [r[0] for r in rows])


if __name__ == "__main__":
    asyncio.run(main())