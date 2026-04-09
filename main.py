"""
ProfServ – Mac-first local expense tracker.

Run with:
    uvicorn main:app --reload --host 127.0.0.1 --port 8000
"""
import logging

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.routes import dashboard, expenses, perdiem, receipts, reports, trips
from app.templating import templates
from bootstrap import bootstrap
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="ProfServ – Expense Tracker", version="1.0.0")

# ── Static files (absolute path so it works regardless of cwd) ────────────────
settings.static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")

# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("Starting ProfServ …")
    bootstrap()
    logger.info("App ready at http://%s:%s", settings.host, settings.port)


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(dashboard.router)
app.include_router(trips.router)
app.include_router(expenses.router)
app.include_router(receipts.router)
app.include_router(perdiem.router)
app.include_router(reports.router)


# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    tb = traceback.format_exc()
    logger.exception("Unhandled error on %s %s", request.method, request.url)
    try:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "detail": f"{type(exc).__name__}: {exc}",
                "traceback": tb,
                "templates_dir": str(settings.templates_dir),
            },
            status_code=500,
        )
    except Exception:
        # Absolute fallback if even error.html can't be rendered
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            f"FATAL: error.html also missing.\n\n"
            f"templates_dir = {settings.templates_dir}\n"
            f"templates_dir exists = {settings.templates_dir.exists()}\n\n"
            f"{tb}",
            status_code=500,
        )
