import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> None:
    engine = create_async_engine("postgresql+asyncpg://violyt:violyt@localhost:5432/violyt")
    async with engine.begin() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT id, name, lifecycle_state, is_finalized "
                    "FROM brand_spaces ORDER BY created_at DESC"
                )
            )
        ).fetchall()
        print("BEFORE:")
        for r in rows:
            print(f"  {r[0]} | {r[1]} | {r[2]} | finalized={r[3]}")

        updated = (
            await conn.execute(
                text(
                    """
                    UPDATE brand_spaces
                    SET lifecycle_state = 'active', is_finalized = true
                    WHERE COALESCE(lifecycle_state, 'draft') NOT IN ('active', 'deleted', 'archived')
                    RETURNING id, name, lifecycle_state
                    """
                )
            )
        ).fetchall()
        print(f"UPDATED: {len(updated)}")
        for r in updated:
            print(f"  {r[0]} | {r[1]} | {r[2]}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
