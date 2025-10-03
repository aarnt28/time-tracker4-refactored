from __future__ import annotations
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .core.config import settings
from .db.session import Base, engine
from .models.ticket import Entry  # noqa: F401 - ensure table metadata loads
from .models.hardware import Hardware  # noqa: F401
from .routers import api_tickets, ui, api_hardware, clients

app = FastAPI(title="Time Tracker", version="1.0.0")

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Static files
app.mount("/static", StaticFiles(directory=str(settings.BASE_DIR / "app" / "static")), name="static")

# Routers
app.include_router(ui.router)
app.include_router(api_tickets.router)
app.include_router(api_hardware.router)
app.include_router(clients.router)

@app.get("/healthz")
def healthz():
    return {"ok": True}
