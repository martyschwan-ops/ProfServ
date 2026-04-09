"""
Manual per-diem entry route.

Per-diem amounts (CAD):
  Breakfast = 20  |  Lunch = 25  |  Dinner = 45
"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.models.expense import (
    Currency, Expense, ExpenseType, PerDiemType, SourceType,
)
from app.services.fx_service import convert_to_cad
from app.services.workbook_service import workbook_service
from app.templating import templates
from config import settings

router = APIRouter(prefix="/perdiem")

_PERDIEM_AMOUNTS = {
    PerDiemType.BREAKFAST: settings.breakfast_amount,
    PerDiemType.LUNCH: settings.lunch_amount,
    PerDiemType.DINNER: settings.dinner_amount,
}


@router.get("/", response_class=HTMLResponse)
async def perdiem_form(request: Request):
    trips = workbook_service.list_trips()
    return templates.TemplateResponse("perdiem/form.html", {
        "request": request,
        "trips": trips,
        "perdiem_types": [p.value for p in PerDiemType],
        "currencies": [c.value for c in Currency],
        "amounts": {p.value: a for p, a in _PERDIEM_AMOUNTS.items()},
        "errors": [],
        "form": {},
    })


@router.post("/")
async def create_perdiem(
    request: Request,
    expense_date: str = Form(...),
    per_diem_type: str = Form(...),
    currency: str = Form("CAD"),
    trip_id: Optional[str] = Form(None),
    exchange_rate_override: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    errors = []
    form_data = {
        "expense_date": expense_date,
        "per_diem_type": per_diem_type,
        "currency": currency,
        "trip_id": trip_id,
        "notes": notes,
    }

    try:
        exp_date = date.fromisoformat(expense_date)
    except ValueError:
        errors.append("Invalid date format. Use YYYY-MM-DD.")
        exp_date = date.today()

    try:
        pd_type = PerDiemType(per_diem_type)
    except ValueError:
        errors.append(f"Invalid per-diem type: {per_diem_type}")
        pd_type = PerDiemType.BREAKFAST

    try:
        cur = Currency(currency)
    except ValueError:
        errors.append(f"Invalid currency: {currency}")
        cur = Currency.CAD

    if errors:
        trips = workbook_service.list_trips()
        return templates.TemplateResponse("perdiem/form.html", {
            "request": request, "trips": trips,
            "perdiem_types": [p.value for p in PerDiemType],
            "currencies": [c.value for c in Currency],
            "amounts": {p.value: a for p, a in _PERDIEM_AMOUNTS.items()},
            "errors": errors, "form": form_data,
        })

    amount_original = _PERDIEM_AMOUNTS[pd_type]
    fx_flag = False

    # Convert string form value to float (empty string → None)
    fx_override: Optional[float] = None
    if exchange_rate_override and exchange_rate_override.strip():
        try:
            fx_override = float(exchange_rate_override.strip())
        except ValueError:
            errors.append("Exchange rate must be a valid number.")

    if cur == Currency.CAD:
        amount_cad = amount_original
        rate: Optional[float] = 1.0
    elif fx_override:
        rate = fx_override
        amount_cad = round(amount_original * rate, 2)
    else:
        amount_cad_val, rate = convert_to_cad(amount_original, exp_date, cur.value)
        if amount_cad_val is None:
            fx_flag = True
            amount_cad = amount_original
            errors.append(
                "Could not retrieve the historical exchange rate. "
                "Enter the rate manually or save and update it later."
            )
        else:
            amount_cad = amount_cad_val

    # If FX failed, show form again so user can enter a manual rate
    if fx_flag:
        trips = workbook_service.list_trips()
        return templates.TemplateResponse("perdiem/form.html", {
            "request": request, "trips": trips,
            "perdiem_types": [p.value for p in PerDiemType],
            "currencies": [c.value for c in Currency],
            "amounts": {p.value: a for p, a in _PERDIEM_AMOUNTS.items()},
            "errors": errors, "form": form_data,
            "show_fx_override": True,
        })

    # Resolve trip
    trip_name = None
    if trip_id:
        trip = workbook_service.get_trip(trip_id)
        if trip:
            trip_name = trip.trip_name
    elif not trip_id:
        # Auto-suggest trip by date
        for t in workbook_service.list_trips():
            if t.contains_date(exp_date):
                trip_id = t.trip_id
                trip_name = t.trip_name
                break

    now = datetime.utcnow()
    expense = Expense(
        expense_id=Expense.new_id(),
        trip_id=trip_id or None,
        trip_name=trip_name,
        expense_date=exp_date,
        vendor_name=f"Per Diem – {pd_type.value}",
        expense_type=ExpenseType.MEAL,
        amount_original=amount_original,
        currency_original=cur,
        exchange_rate_to_cad=rate,
        amount_cad=amount_cad,
        gst_original=None,
        gst_cad=None,
        source_type=SourceType.PER_DIEM,
        per_diem_type=pd_type,
        notes=notes.strip() if notes else None,
        submitted_status=False,
        created_at=now,
        updated_at=now,
    )

    try:
        workbook_service.save_expense(expense)
    except IOError as exc:
        errors.append(str(exc))
        trips = workbook_service.list_trips()
        return templates.TemplateResponse("perdiem/form.html", {
            "request": request, "trips": trips,
            "perdiem_types": [p.value for p in PerDiemType],
            "currencies": [c.value for c in Currency],
            "amounts": {p.value: a for p, a in _PERDIEM_AMOUNTS.items()},
            "errors": errors, "form": form_data,
        })

    return RedirectResponse("/expenses/", status_code=303)
