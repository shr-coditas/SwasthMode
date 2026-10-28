from celery import Celery
from app.core.config import settings

celery = Celery("swasthmode", broker=settings().redis_url.get_secret_value(),
                backend=settings().redis_url.get_secret_value(), include=["app.tasks.meal_insights"])
celery.conf.update(
    accept_content=["json"], task_serializer="json", result_serializer="json",
    task_track_started=True, result_expires=86400, worker_prefetch_multiplier=1,
    task_publish_retry=False, broker_connection_timeout=3,
    broker_transport_options={"socket_connect_timeout": 3, "socket_timeout": 3},
    result_backend_transport_options={"socket_connect_timeout": 3, "socket_timeout": 3},
    task_acks_late=True, task_reject_on_worker_lost=True,
    task_soft_time_limit=85, task_time_limit=95,
)
