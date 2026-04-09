from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.models.expense import Currency, Expense, ExpenseFilter, ExpenseType, SourceType
from app.services.workbook_service import workbook_service
from app.templating import templates

router = APIRouter(prefix="/expenses")


def _build_filter(request: Request) -> ExpenseFilter:
    q = request.query_params
    return ExpenseFilter(
        trip_id=q.get("trip_id") or None,
        date_from=q.get("date_from") or None,
        date_to=q.get("date_to") or None,
        expense_type=q.get("expense_type") or None,
        vendor=q.get("vendor") or None,
        currency=q.get("currency") or None,
        submitted={"true": True, "false": False}.get(q.get("submitted", ""), None),
        search=q.get("search") or None,
    )


@router.get("/", response_class=HTMLResponse)
async def list_expenses(request: Request):
    f = _build_filter(request)
    expenses = workbook_service.list_expenses(f)
    trips = workbook_service.list_trips()
    return templates.TemplateResponse("expenses/list.html", {
        "request": request,
        "expenses": expenses,
        "trips": trips,
        "expense_types": [e.value for e in ExpenseType],
        "currencies": [c.value for c in Currency],
        "filter": f,
        "total_cad": sum(e.amount_cad for e in expenses),
    })


@router.get("/{expense_id}/edit", response_class=HTMLResponse)
async def edit_expense_form(request: Request, expense_id: str):
    expense = workbook_service.get_expense(expense_id)
    if not expense:
        return RedirectResponse("/expenses/", status_code=303)
    trips = workbook_service.list_trips()
    return templates.TemplateResponse("expenses/edit.html", {
        "request": request,
        "expense": expense,
        "trips": trips,
        "expense_types": [e.value for e in ExpenseType],
        "currencies": [c.value for c in Currency],
        "errors": [],
    })


@router.post("/{expense_id}/edit")
async def update_expense(
    request: Request,
    expense_id: str,
    expense_date: str = Form(...),
    vendor_name: str = Form(""),
    expense_type: str = Form("Unknown"),
    amount_original: float = Form(...),
    currency_original: str = Form("CAD"),
    exchange_rate_to_cad: Optional[float] = Form(None),
    amount_cad: Optional[float] = Form(None),
    gst_original: Optional[float] = Form(None),
    trip_id: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    submitted_status: Optional[str] = Form(None),
):
    errors = []
    expense = workbook_service.get_expense(expense_id)
    if not expense:
        return RedirectResponse("/expenses/", status_code=303)

    try:
        exp_date = date.fromisoformat(expense_date)
    except ValueError:
        errors.append("Invalid expense date.")
        exp_date = expense.expense_date

    if amount_original <= 0:
        errors.append("Amount must be greater than zero.")

    # Resolve trip
    trip_name = None
    if trip_id:
        trip = workbook_service.get_trip(trip_id)
        if trip:
            trip_name = trip.trip_name

    # FX conversion
    if currency_original == "CAD":
        final_amount_cad = amount_original
        final_rate = 1.0
    else:
        if amount_cad and amount_cad > 0:
            final_amount_cad = amount_cad
            final_rate = exchange_rate_to_cad or (amount_cad / amount_original if amount_original else None)
        else:
            from app.services.fx_service import convert_to_cad
            cad, rate = convert_to_cad(amount_original, exp_date, currency_original)
            final_amount_cad = cad or amount_original
            final_rate = rate

    gst_cad = None
    if gst_original:
        if currency_original == "CAD":
            gst_cad = gst_original
        elif final_rate:
            gst_cad = round(gst_original * final_rate, 2)

    if errors:
        trips = workbook_service.list_trips()
        return templates.TemplateResponse("expenses/edit.html", {
            "request": request, "expense": expense, "trips": trips,
            "expense_types": [e.value for e in ExpenseType],
            "currencies": [c.value for c in Currency],
            "errors": errors,
        })

    expense.expense_date = exp_date
    expense.vendor_name = vendor_name.strip() or None
    expense.expense_type = ExpenseType(expense_type)
    expense.amount_original = amount_original
    expense.currency_original = Currency(currency_original)
    expense.exchange_rate_to_cad = final_rate
    expense.amount_cad = final_amount_cad
    expense.gst_original = gst_original
    expense.gst_cad = gst_cad
    expense.trip_id = trip_id or None
    expense.trip_name = trip_name
    expense.notes = notes.strip() if notes else None
    expense.submitted_status = submitted_status == "on"
    expense.updated_at = datetime.utcnow()

    try:
        workbook_service.save_expense(expense)
    except IOError as exc:
        errors.append(str(exc))
        trips = workbook_service.list_trips()
        return templates.TemplateResponse("expenses/edit.html", {
            "request": request, "expense": expense, "trips": trips,
            "expense_types": [e.value for e in ExpenseType],
            "currencies": [c.value for c in Currency],
            "errors": errors,
        })

    return RedirectResponse("/expenses/", status_code=303)


@router.post("/{expense_id}/delete")
async def delete_expense(expense_id: str):
    workbook_service.delete_expense(expense_id)
    return RedirectResponse("/expenses/", status_code=303)


@router.post("/{expense_id}/toggle-submitted")
async def toggle_submitted(expense_id: str):
    expense = workbook_service.get_expense(expense_id)
    if expense:
        expense.submitted_status = not expense.submitted_status
        expense.updated_at = datetime.utcnow()
        workbook_service.save_expense(expense)
    return RedirectResponse("/expenses/", status_code=303)


@router.get("/export/csv")
async def export_csv(request: Request):
    import csv, io
    f = _build_filter(request)
    expenses = workbook_service.list_expenses(f)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Expense ID", "Trip Name", "Expense Date", "Vendor Name", "Expense Type",
        "Amount Original", "Currency Original", "Exchange Rate", "Amount CAD",
        "GST Original", "GST CAD", "Source Type", "Per Diem Type",
        "Receipt File Name", "Notes", "Submitted",
    ])
    for e in expenses:
        writer.writerow([
            e.expense_id, e.trip_name, e.expense_date.isoformat(), e.vendor_name,
            e.expense_type.value, e.amount_original, e.currency_original.value,
            e.exchange_rate_to_cad, e.amount_cad, e.gst_original, e.gst_cad,
            e.source_type.value, e.per_diem_type.value if e.per_diem_type else "",
            e.receipt_file_name, e.notes, e.submitted_status,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenses.csv"},
    )
