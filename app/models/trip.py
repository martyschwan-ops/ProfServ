from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, field_validator
import uuid


class TripCreate(BaseModel):
    trip_name: str
    start_date: date
    end_date: date
    notes: Optional[str] = None

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: date, info) -> date:
        start = info.data.get("start_date")
        if start and v < start:
            raise ValueError("end_date must be on or after start_date")
        return v


class Trip(BaseModel):
    trip_id: str
    trip_name: str
    start_date: date
    end_date: date
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    def contains_date(self, d: date) -> bool:
        return self.start_date <= d <= self.end_date

    @classmethod
    def new(cls, data: TripCreate) -> "Trip":
        now = datetime.utcnow()
        return cls(
            trip_id=str(uuid.uuid4()),
            trip_name=data.trip_name,
            start_date=data.start_date,
            end_date=data.end_date,
            notes=data.notes,
            created_at=now,
            updated_at=now,
        )
