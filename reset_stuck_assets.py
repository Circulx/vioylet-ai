"""
Reset stuck assets back to 'uploaded' state so they can be reprocessed.

Usage:
    python reset_stuck_assets.py              # dry-run (show what would change)
    python reset_stuck_assets.py --fix        # apply the reset
    python reset_stuck_assets.py --fix --all  # also reset 'failed' assets
"""
import asyncio
import sys
from sqlalchemy import select, update
from app.db.session import AsyncSessionLocal
from app.models.knowledge import KnowledgeAsset

BRAND_ID = "1eeb4475-24ca-41dd-8cad-80bb50e0ca74"


async def reset_stuck(apply: bool = False, include_failed: bool = False):
    async with AsyncSessionLocal() as session:
        # ── Show current summary ──────────────────────────────────────────────
        from sqlalchemy import func
        summary_q = (
            select(KnowledgeAsset.lifecycle_state, func.count())
            .where(KnowledgeAsset.brand_space_id == BRAND_ID)
            .group_by(KnowledgeAsset.lifecycle_state)
        )
        rows = (await session.execute(summary_q)).all()
        print(f"\nCurrent state for brand {BRAND_ID}:")
        for state, count in rows:
            print(f"  {state:12s}: {count}")

        # ── Find stuck assets ─────────────────────────────────────────────────
        stuck_states = ["processing"]
        if include_failed:
            stuck_states.append("failed")

        stuck_q = select(KnowledgeAsset).where(
            KnowledgeAsset.brand_space_id == BRAND_ID,
            KnowledgeAsset.lifecycle_state.in_(stuck_states),
        )
        stuck_assets = (await session.execute(stuck_q)).scalars().all()

        if not stuck_assets:
            print(f"\nNo assets in {stuck_states} state — nothing to reset.")
            return

        print(f"\nAssets to reset → 'uploaded' ({len(stuck_assets)} total):")
        for a in stuck_assets:
            print(f"  [{a.lifecycle_state:12s}] {a.name}")
            if a.processing_error:
                print(f"               error: {a.processing_error[:120]}")

        if not apply:
            print("\n[DRY RUN] Pass --fix to apply the reset.")
            return

        # ── Apply reset ───────────────────────────────────────────────────────
        for a in stuck_assets:
            a.lifecycle_state = "uploaded"
            a.processing_error = None
        await session.commit()
        print(f"\n✓ Reset {len(stuck_assets)} asset(s) to 'uploaded'. They will be picked up on next worker run.")

        # ── Show updated summary ──────────────────────────────────────────────
        rows2 = (await session.execute(summary_q)).all()
        print("\nUpdated state:")
        for state, count in rows2:
            print(f"  {state:12s}: {count}")


if __name__ == "__main__":
    apply  = "--fix"  in sys.argv
    all_   = "--all"  in sys.argv
    asyncio.run(reset_stuck(apply=apply, include_failed=all_))
