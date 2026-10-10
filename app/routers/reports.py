from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..services import BillingService
from ..schemas import DailyReport

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/daily", response_model=DailyReport)
def daily_sales(on_date: date, db: Session = Depends(get_db)):
    """Total sales and completed appointments for a day, per barber."""
    return BillingService(db).daily_report(on_date)
