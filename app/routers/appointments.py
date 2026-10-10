from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..services import AppointmentService, BillingService
from ..schemas import (AppointmentCreate, AppointmentUpdate, AppointmentOut,
                       StatusUpdate, CheckoutRequest, CheckoutOut)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


def svc(db: Session = Depends(get_db)) -> AppointmentService:
    return AppointmentService(db)


@router.post("", response_model=AppointmentOut, status_code=201)
def book_appointment(data: AppointmentCreate, s: AppointmentService = Depends(svc)):
    return s.book(**data.model_dump())


@router.get("", response_model=list[AppointmentOut])
def list_appointments(barber_id: int | None = None, customer_id: int | None = None,
                      on_date: date | None = None, status: str | None = None,
                      s: AppointmentService = Depends(svc)):
    return s.list(barber_id, customer_id, on_date, status)


@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(appointment_id: int, s: AppointmentService = Depends(svc)):
    return s.get(appointment_id)


@router.put("/{appointment_id}", response_model=AppointmentOut)
def reschedule_appointment(appointment_id: int, data: AppointmentUpdate,
                           s: AppointmentService = Depends(svc)):
    return s.reschedule(appointment_id, data.model_dump(exclude_unset=True))


@router.patch("/{appointment_id}/status", response_model=AppointmentOut)
def update_status(appointment_id: int, data: StatusUpdate, s: AppointmentService = Depends(svc)):
    return s.set_status(appointment_id, data.status)


@router.post("/{appointment_id}/checkout", response_model=CheckoutOut)
def checkout_appointment(appointment_id: int, data: CheckoutRequest,
                         db: Session = Depends(get_db)):
    """Transaction: records the payment and completes the appointment together."""
    appt, payment, change = BillingService(db).checkout(
        appointment_id, data.method, data.amount_tendered)
    return {"appointment": appt, "payment": payment, "change": change}


@router.delete("/{appointment_id}", status_code=204)
def delete_appointment(appointment_id: int, s: AppointmentService = Depends(svc)):
    s.delete(appointment_id)
