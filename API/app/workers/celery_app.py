import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - ambiente minimo sem python-dotenv instalado
    def load_dotenv(*args, **kwargs):
        return False


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

try:
    from celery import Celery
    from kombu import Exchange, Queue
except ImportError:  # pragma: no cover - fallback para ambientes de teste sem dependencias instaladas
    Celery = None
    Exchange = None
    Queue = None


redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

if Celery is None:
    class _Task:
        def __init__(self, func):
            self.func = func

        def run(self, *args, **kwargs):
            return self.func(*args, **kwargs)

        def apply_async(self, args=None, kwargs=None, queue=None):
            raise RuntimeError("Celery nao esta instalado neste ambiente.")

        def __call__(self, *args, **kwargs):
            return self.func(*args, **kwargs)

    class _CeleryFallback:
        def task(self, *args, **kwargs):
            def decorator(func):
                return _Task(func)

            return decorator

    celery_app = _CeleryFallback()
else:
    celery_app = Celery(
        "plataforma_fiscal",
        broker=redis_url,
        backend=os.getenv("CELERY_RESULT_BACKEND", redis_url),
        include=[
            "app.workers.nfe_tasks",
            "app.workers.sped_tasks",
        ],
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone=os.getenv("TZ", "America/Sao_Paulo"),
        enable_utc=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_default_queue="default",
        task_queues=(
            Queue("default", Exchange("default"), routing_key="default"),
            Queue("nfe", Exchange("nfe"), routing_key="nfe"),
            Queue("sped", Exchange("sped"), routing_key="sped"),
        ),
    )

    if os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() in {"1", "true", "yes"}:
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True
