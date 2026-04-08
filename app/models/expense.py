from datetime import date, datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, field_validator
import uuid


class ExpenseType(str, Enum):
    MEAL = "Meal"
    HOTEL = "Hotel"
    AIRFARE = "Airfare"
    CAR_RENTAL = "Car Rental"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class PerDiemType(str, Enum):
    BREAKFAST = "Breakfast"
    LUNCH = "Lunch"
    DINNER = "Dinner"


class SourceType(str, Enum):
    RECEIPT = "Receipt"
    PER_DIEM = "Per Diem"
    MANUAL = "Manual"


class Currency(str, Enum):
    CAD = "CAD"
    USD = "USD"


class Expense(BaseModel):
    expense_id: str
    trip_id: Optional[str] = None
    trip_name: Optional[str] = None
    expense_date: date
    vendor_name: Optional[str] = None
    expense_type: ExpenseType = ExpenseType.UNKNOWN
    amount_original: float
    currency_original: Currency = Currency.CAD
    exchange_rate_to_cad: Optional[float] = None
    amount_cad: float
    gst_original: Optional[float] = None
    gst_cad: Optional[float] = None
    source_type: SourceType = SourceType.MANUAL
    per_diem_type: Optional[PerDiemType] = None
    receipt_file_name: Optional[str] = None
    receipt_file_path: Optional[str] = None
    notes: Optional[str] = None
    submitted_status: bool = False
    created_at: datetime
    updated_at: datetime

    @classmethod
    def new_id(cls) -> str:
        return str(uuid.uuid4())


class ExtractionResult(BaseModel):
    expense_date: Optional[date] = None
    vendor_name: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    gst_amount: Optional[float] = None
    expense_type: Optional[str] = None
    raw_text: str = ""
    confidence: float = 0.0
    flags: List[str] = []


class ReceiptReviewForm(BaseModel):
    """Submitted by the user after reviewing extraction results."""
    expense_date: date
    vendor_name: str
    expense_type: ExpenseType = ExpenseType.UNKNOWN
    amount_original: float
    currency_original: Currency = Currency.CAD
    gst_original: Optional[float] = None
    trip_id: Optional[str] = None
    notes: Optional[str] = None
    temp_file_key: str  # key to locate the uploaded temp file


class PerDiemForm(BaseModel):
    expense_date: date
    trip_id: Optional[str] = None
    per_diem_type: PerDiemType
    currency: Currency = Currency.CAD
    notes: Optional[str] = None


class ExpenseFilter(BaseModel):
    trip_id: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    expense_type: Optional[ExpenseType] = None
    vendor: Optional[str] = None
    currency: Optional[Currency] = None
    submitted: Optional[bool] = None
    search: Optional[str] = None
