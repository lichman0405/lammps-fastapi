from celery import Celery
import structlog

from app.core.config import settings

# 创建Celery实例
celery_app = Celery(
    "lammps_mcp",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.simulation_tasks"]
)

# 配置Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 任务最大执行时间1小时
    task_soft_time_limit=3300,  # 软限制55分钟
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# 配置日志
logger = structlog.get_logger(__name__)

@celery_app.task(bind=True)
def debug_task(self):
    """调试任务"""
    logger.info("Debug task executed", task_id=self.request.id)
    return {"task_id": self.request.id}

# 任务状态常量
class TaskStatus:
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"