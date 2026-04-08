from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.workbook_service import workbook_service

router = APIRouter(prefix="/reports")
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def reports(request: Request):
    by_trip = workbook_service.summary_by_trip()
    by_type = workbook_service.summary_by_type()
    by_month = workbook_service.summary_by_month()
    total_gst = workbook_service.total_gst()
    total_cad = workbook_service.total_cad()

    return templates.TemplateResponse("reports/index.html", {
        "request": request,
        "by_trip": by_trip,
        "by_type": by_type,
        "by_month": by_month,
        "total_gst": total_gst,
        "total_cad": total_cad,
    })
