import asyncio

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.graph.models.layer1_models import BrandContextOutput
from app.graph.state import ViolytState
from app.models.brand import BrandSpace
from app.models.retrieval_log import RetrievalLog

logger = get_logger(__name__)


async def layer1_retrieval(state: ViolytState) -> dict:
    from app.services.vectorstore.retrieval_service import BrandRetrievalService

    brand_id = state.get("brand_id", "unknown")
    user_prompt = state.get("user_prompt", "")
    platform = state.get("platform", "")
    format = state.get("format", "")

    service = BrandRetrievalService()
    try:
        result = await asyncio.to_thread(
            service.retrieve,
            brand_id=brand_id,
            user_prompt=user_prompt,
            platform=platform,
            format=format,
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"layer1_retrieval failed brand_id={brand_id}: {e}")
        return {
            "brand_context": BrandContextOutput(
                brand_id=brand_id,
                retrieved_sections=[],
                high_relevance_context=[],
                medium_relevance_context=[],
                low_relevance_context=[],
                missing_context=["retrieval_error"],
                brand_isolation_status="fail",
                retrieval_confidence=0.0,
                retrieval_query=service.build_query(user_prompt, brand_id, platform, format),
                total_chunks_retrieved=0,
            ),
            "error": f"Layer 1 retrieval failed: {e}",
        }

    output: BrandContextOutput = result["output"]
    log = result["retrieval_log"]
    update: dict = {
        "brand_context": output,
        "retrieval_log": log,
    }

    try:
        async with AsyncSessionLocal() as session:
            brand = await session.get(BrandSpace, brand_id)
            if brand is None:
                logger.warning(
                    f"layer1_retrieval skipping log persistence: brand {brand_id} not found"
                )
            else:
                session.add(
                    RetrievalLog(
                        tenant_id=brand.tenant_id,
                        brand_space_id=brand_id,
                        query=log["query"],
                        namespace=log["namespace"],
                        isolation_status=output.brand_isolation_status,
                        confidence=output.retrieval_confidence,
                        total_chunks=log["total_chunks"],
                        chunks=log["chunks"],
                        metadata_json={
                            "user_prompt": user_prompt,
                            "platform": platform,
                            "format": format,
                        },
                    )
                )
                await session.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"layer1_retrieval failed to persist retrieval log: {e}")

    # Hard abort downstream layers if brand isolation could not be guaranteed.
    if output.brand_isolation_status == "fail":
        update["error"] = "Brand isolation failed: no brand data retrieved."

    return update
