"""
Receipt upload and review routes.

Flow:
  GET  /receipts/upload        → upload form
  POST /receipts/upload        → save temp file, run pipeline, redirect to review
  GET  /receipts/review/{key}  → show extracted fields for user correction
  POST /receipts/confirm/{key} → user confirms/edits fields → save expense + move file
"""
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.models.expense import (
    Currency, Expense, ExpenseType, ExtractionResult, SourceType,
)
from app.services import file_storage_service as fss
from app.services.receipt_pipeline import run_pipeline
from app.services.workbook_service import workbook_service
from config import settings

router = APIRouter(prefix="/receipts")
templates = Jinja2Templates(directory=str(settings.templates_dir))

# In-memory session store for pending extractions keyed by temp_key.
# Fine for single-user local app.
_pending: dict[str, dict] = {}


@router.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request):
    trips = workbook_service.list_trips()
    return templates.TemplateResponse("receipts/upload.html", {
        "request": request, "trips": trips,
    })


@router.post("/upload")
async def upload_receipt(
    request: Request,
    file: UploadFile = File(...),
    trip_id: Optional[str] = Form(None),
):
    content = await file.read()
    if not content:
        trips = workbook_service.list_trips()
        return templates.TemplateResponse("receipts/upload.html", {
            "request": request, "trips": trips,
            "error": "Uploaded file is empty.",
        })

    temp_key, temp_path = fss.save_temp_upload(file.filename or "receipt.bin", content)

    # Run extraction pipeline
    result: ExtractionResult = run_pipeline(temp_path)

    # Suggest trip if not provided
    if not trip_id and result.expense_date:
        trips = workbook_service.list_trips()
        for t in trips:
            if t.contains_date(result.expense_date):
                trip_id = t.trip_id
                break

    _pending[temp_key] = {
        "result": result,
        "trip_id": trip_id,
        "original_filename": file.filename,
    }

    return RedirectResponse(f"/receipts/review/{temp_key}", status_code=303)


@router.get("/review/{temp_key}", response_class=HTMLResponse)
async def review_form(request: Request, temp_key: str):
    pending = _pending.get(temp_key)
    if not pending:
        return RedirectResponse("/receipts/upload", status_code=303)

    result: ExtractionResult = pending["result"]
    trips = workbook_service.list_trips()

    return templates.TemplateResponse("receipts/review.html", {
        "request": request,
        "result": result,
        "temp_key": temp_key,
        "trips": trips,
        "expense_types": [e.value for e in ExpenseType],
        "currencies": [c.value for c in Currency],
        "suggested_trip_id": pending.get("trip_id"),
        "original_filename": pending.get("original_filename"),
        "errors": [],
    })


@router.post("/confirm/{temp_key}")
async def confirm_receipt(
    request: Request,
    temp_key: str,
    expense_date: str = Form(...),
    vendor_name: str = Form(...),
    expense_type: str = Form("Unknown"),
    amount_original: float = Form(...),
    currency_original: str = Form("CAD"),
    exchange_rate_override: Optional[float] = Form(None),
    gst_original: Optional[float] = Form(None),
    trip_id: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    errors = []
    pending = _pending.get(temp_key)
    if not pending:
        return RedirectResponse("/receipts/upload", status_code=303)

    # Validation
    try:
        exp_date = date.fromisoformat(expense_date)
    except ValueError:
        errors.append("Invalid expense date format.")
        exp_date = date.today()

    vendor_name = vendor_name.strip()
    if not vendor_name:
        errors.append("Vendor name cannot be blank.")

    if amount_original <= 0:
        errors.append("Amount must be greater than zero.")

    if gst_original and amount_original and gst_original > amount_original:
        errors.append("GST cannot exceed total amount.")

    if errors:
        result = pending["result"]
        trips = workbook_service.list_trips()
        return templates.TemplateResponse("receipts/review.html", {
            "request": request, "result": result, "temp_key": temp_key,
            "trips": trips, "expense_types": [e.value for e in ExpenseType],
            "currencies": [c.value for c in Currency],
            "suggested_trip_id": trip_id,
            "original_filename": pending.get("original_filename"),
            "errors": errors,
        })

    # FX conversion
    from app.services.fx_service import convert_to_cad
    fx_flag = False
    if currency_original == "CAD":
        amount_cad = amount_original
        rate = 1.0
    elif exchange_rate_override:
        rate = exchange_rate_override
        amount_cad = round(amount_original * rate, 2)
    else:
        amount_cad_val, rate = convert_to_cad(amount_original, exp_date, currency_original)
        if amount_cad_val is None:
            fx_flag = True
            amount_cad = amount_original
            rate = None
        else:
            amount_cad = amount_cad_val

    gst_cad = None
    if gst_original:
        if currency_original == "CAD":
            gst_cad = gst_original
        elif rate:
            gst_cad = round(gst_original * rate, 2)

    # Resolve trip
    trip_name = None
    if trip_id:
        trip = workbook_service.get_trip(trip_id)
        if trip:
            trip_name = trip.trip_name

    # Move + rename file
    temp_path = fss.get_temp_path(temp_key)
    receipt_file_name = None
    receipt_file_path = None
    if temp_path:
        try:
            receipt_file_name, receipt_file_path = fss.store_receipt(
                temp_path, exp_date, vendor_name, trip_name
            )
        except Exception as exc:
            errors.append(f"File storage error: {exc}")

    # Build and save expense
    now = datetime.utcnow()
    expense = Expense(
        expense_id=Expense.new_id(),
        trip_id=trip_id or None,
        trip_name=trip_name,
        expense_date=exp_date,
        vendor_name=vendor_name,
        expense_type=ExpenseType(expense_type),
        amount_original=amount_original,
        currency_original=Currency(currency_original),
        exchange_rate_to_cad=rate,
        amount_cad=amount_cad,
        gst_original=gst_original,
        gst_cad=gst_cad,
        source_type=SourceType.RECEIPT,
        receipt_file_name=receipt_file_name,
        receipt_file_path=receipt_file_path,
        notes=(notes.strip() if notes else None) or ("FX rate unavailable – verify" if fx_flag else None),
        submitted_status=False,
        created_at=now,
        updated_at=now,
    )

    try:
        workbook_service.save_expense(expense)
    except IOError as exc:
        errors.append(str(exc))
        result = pending["result"]
        trips = workbook_service.list_trips()
        return templates.TemplateResponse("receipts/review.html", {
            "request": request, "result": result, "temp_key": temp_key,
            "trips": trips, "expense_types": [e.value for e in ExpenseType],
            "currencies": [c.value for c in Currency],
            "suggested_trip_id": trip_id,
            "original_filename": pending.get("original_filename"),
            "errors": errors,
        })

    # Clean up
    _pending.pop(temp_key, None)
    fss.delete_temp(temp_key)

    return RedirectResponse(f"/expenses/{expense.expense_id}/edit", status_code=303)
