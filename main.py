"""
ProfServ – Mac-first local expense tracker.

Run with:
    uvicorn main:app --reload --host 127.0.0.1 --port 8000
"""
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes import dashboard, expenses, perdiem, receipts, reports, trips
from bootstrap import bootstrap
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="ProfServ – Expense Tracker", version="1.0.0")

# ── Static files ──────────────────────────────────────────────────────────────
static_dir = Path("app/static")
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ── Templates ─────────────────────────────────────────────────────────────────
templates = Jinja2Templates(directory="app/templates")


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
    logger.exception("Unhandled error on %s %s", request.method, request.url)
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "detail": str(exc)},
        status_code=500,
    )
