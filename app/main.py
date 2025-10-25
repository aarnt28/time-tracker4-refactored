from prometheus_fastapi_instrumentator import Instrumentator

from app.core.logging import setup_logging
from app.core.settings import settings
from . import app as legacy_app

setup_logging()
app = legacy_app
app.title = settings.APP_NAME
instrumentator = Instrumentator()


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.on_event("startup")
async def _metrics() -> None:
    instrumentator.instrument(app).expose(app)
