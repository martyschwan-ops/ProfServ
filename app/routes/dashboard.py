from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.workbook_service import workbook_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    expenses = workbook_service.list_expenses()
    trips = workbook_service.list_trips()
    total_cad = workbook_service.total_cad()
    total_gst = workbook_service.total_gst()
    by_type = workbook_service.summary_by_type()
    by_trip = workbook_service.summary_by_trip()

    recent = sorted(expenses, key=lambda e: e.created_at, reverse=True)[:10]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_cad": total_cad,
        "total_gst": total_gst,
        "expense_count": len(expenses),
        "trip_count": len(trips),
        "by_type": by_type,
        "by_trip": by_trip,
        "recent": recent,
    })
