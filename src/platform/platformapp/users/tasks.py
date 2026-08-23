import structlog
from celery import shared_task

from .models import User

logger = structlog.get_logger(__name__)


@shared_task()
def get_users_count():
    """A pointless Celery task to demonstrate usage (and CAP-2 hop correlation)."""
    count = User.objects.count()
    logger.info("celery_users_count", user_count=count)
    return count
