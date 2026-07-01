"""Celery worker for document ingestion tasks."""

from celery import Celery
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.vectorstore.ingestion_service import IngestionService

logger = get_logger(__name__)

# Initialize Celery app with Redis broker
celery_app = Celery(
    "ingestion_worker",
    broker=get_settings().celery_broker_url,
    backend=get_settings().celery_broker_url,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    track_started=True,
)


@celery_app.task(bind=True, max_retries=3)
def process_document_ingestion(self, brand_id: str, file_path: str) -> dict:
    """Process a document for ingestion into Pinecone.

    Args:
        brand_id: Brand ID for namespace isolation
        file_path: Path to the document file

    Returns:
        Dictionary with processing results
    """
    logger.info(f"Starting document ingestion task for brand: {brand_id}, file: {file_path}")

    try:
        ingestion_service = IngestionService()
        result = ingestion_service.process_document(brand_id, file_path)
        logger.info(f"Document ingestion completed successfully: {result}")
        return result

    except Exception as e:
        logger.error(f"Document ingestion failed: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


def process_document_sync(brand_id: str, file_path: str) -> dict:
    """Synchronous fallback for document processing when Celery is unavailable.

    Args:
        brand_id: Brand ID for namespace isolation
        file_path: Path to the document file

    Returns:
        Dictionary with processing results
    """
    logger.info(f"Running synchronous document ingestion for brand: {brand_id}, file: {file_path}")

    try:
        ingestion_service = IngestionService()
        result = ingestion_service.process_document(brand_id, file_path)
        logger.info(f"Synchronous document ingestion completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Synchronous document ingestion failed: {e}")
        raise
