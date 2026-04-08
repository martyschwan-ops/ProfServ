from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.models.trip import Trip, TripCreate
from app.services.workbook_service import workbook_service
from config import settings

router = APIRouter(prefix="/trips")
templates = Jinja2Templates(directory=str(settings.templates_dir))


@router.get("/", response_class=HTMLResponse)
async def list_trips(request: Request):
    trips = workbook_service.list_trips()
    trips_sorted = sorted(trips, key=lambda t: t.start_date, reverse=True)
    return templates.TemplateResponse("trips/list.html", {"request": request, "trips": trips_sorted})


@router.get("/new", response_class=HTMLResponse)
async def new_trip_form(request: Request):
    return templates.TemplateResponse("trips/form.html", {"request": request, "trip": None, "errors": []})


@router.post("/new")
async def create_trip(
    request: Request,
    trip_name: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    notes: Optional[str] = Form(None),
):
    errors = []
    try:
        data = TripCreate(
            trip_name=trip_name.strip(),
            start_date=start_date,
            end_date=end_date,
            notes=notes.strip() if notes else None,
        )
    except Exception as exc:
        errors.append(str(exc))
        return templates.TemplateResponse("trips/form.html", {
            "request": request, "trip": None,
            "errors": errors,
            "form": {"trip_name": trip_name, "start_date": start_date,
                     "end_date": end_date, "notes": notes},
        })

    trip = Trip.new(data)
    try:
        workbook_service.save_trip(trip)
    except IOError as exc:
        errors.append(str(exc))
        return templates.TemplateResponse("trips/form.html", {
            "request": request, "trip": None, "errors": errors,
        })
    return RedirectResponse("/trips/", status_code=303)


@router.get("/{trip_id}/edit", response_class=HTMLResponse)
async def edit_trip_form(request: Request, trip_id: str):
    trip = workbook_service.get_trip(trip_id)
    if not trip:
        return RedirectResponse("/trips/", status_code=303)
    return templates.TemplateResponse("trips/form.html", {"request": request, "trip": trip, "errors": []})


@router.post("/{trip_id}/edit")
async def update_trip(
    request: Request,
    trip_id: str,
    trip_name: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    notes: Optional[str] = Form(None),
):
    errors = []
    trip = workbook_service.get_trip(trip_id)
    if not trip:
        return RedirectResponse("/trips/", status_code=303)

    try:
        data = TripCreate(
            trip_name=trip_name.strip(),
            start_date=start_date,
            end_date=end_date,
            notes=notes.strip() if notes else None,
        )
    except Exception as exc:
        errors.append(str(exc))
        return templates.TemplateResponse("trips/form.html", {
            "request": request, "trip": trip, "errors": errors,
        })

    trip.trip_name = data.trip_name
    trip.start_date = data.start_date
    trip.end_date = data.end_date
    trip.notes = data.notes
    trip.updated_at = datetime.utcnow()

    try:
        workbook_service.save_trip(trip)
    except IOError as exc:
        errors.append(str(exc))
        return templates.TemplateResponse("trips/form.html", {
            "request": request, "trip": trip, "errors": errors,
        })
    return RedirectResponse("/trips/", status_code=303)


@router.post("/{trip_id}/delete")
async def delete_trip(trip_id: str):
    workbook_service.delete_trip(trip_id)
    return RedirectResponse("/trips/", status_code=303)
