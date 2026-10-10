from __future__ import annotations
"""Service classes: business rules / workflows that involve several tables.

AppointmentService  -> booking, rescheduling, availability
BillingService      -> checkout (a database TRANSACTION) and sales reports
"""
from datetime import date, datetime, time, timedelta
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .models import Appointment, Barber, Customer, Service, Payment
from .repositories import CustomerRepository, BarberRepository, ServiceRepository

OPEN_TIME = time(9, 0)    # shop opening hour
CLOSE_TIME = time(19, 0)  # shop closing hour
SLOT_STEP = 30            # minutes between possible start times


class AppointmentService:
    def __init__(self, db: Session):
        self._db = db
        self._customers = CustomerRepository(db)
        self._barbers = BarberRepository(db)
        self._services = ServiceRepository(db)

    # ---------- helpers ----------
    def get(self, appointment_id: int) -> Appointment:
        appt = self._db.get(Appointment, appointment_id)
        if not appt:
            raise HTTPException(404, "Appointment not found")
        return appt

    def _ensure_barber_free(self, barber_id: int, start: datetime, end: datetime,
                            exclude_id: int | None = None) -> None:
        stmt = select(Appointment).where(
            Appointment.barber_id == barber_id,
            Appointment.status != "cancelled",
            Appointment.start_time < end,
            Appointment.end_time > start,
        )
        if exclude_id:
            stmt = stmt.where(Appointment.id != exclude_id)
        if self._db.scalars(stmt).first():
            raise HTTPException(409, "Barber is not available at that time")

    # ---------- workflow 1: booking ----------
    def book(self, customer_id: int, barber_id: int, service_id: int,
             start_time: datetime, notes: str | None = None) -> Appointment:
        self._customers.get(customer_id)
        barber = self._barbers.get(barber_id)
        service = self._services.get(service_id)

        if not barber.is_active:
            raise HTTPException(400, "Barber is not active")
        if start_time < datetime.now():
            raise HTTPException(400, "Cannot book an appointment in the past")

        end = start_time + timedelta(minutes=service.duration_minutes)
        self._ensure_barber_free(barber_id, start_time, end)

        appt = Appointment(customer_id=customer_id, barber_id=barber_id, service_id=service_id,
                           start_time=start_time, end_time=end, status="pending", notes=notes)
        self._db.add(appt)
        self._db.commit()
        self._db.refresh(appt)
        return appt

    def list(self, barber_id=None, customer_id=None, on_date: date | None = None, status=None):
        stmt = select(Appointment).order_by(Appointment.start_time)
        if barber_id:
            stmt = stmt.where(Appointment.barber_id == barber_id)
        if customer_id:
            stmt = stmt.where(Appointment.customer_id == customer_id)
        if status:
            stmt = stmt.where(Appointment.status == status)
        if on_date:
            day = datetime.combine(on_date, time.min)
            stmt = stmt.where(Appointment.start_time >= day,
                              Appointment.start_time < day + timedelta(days=1))
        return list(self._db.scalars(stmt).all())

    def reschedule(self, appointment_id: int, changes: dict) -> Appointment:
        appt = self.get(appointment_id)
        if appt.status in ("completed", "cancelled"):
            raise HTTPException(400, f"Cannot edit a {appt.status} appointment")

        barber_id = changes.get("barber_id", appt.barber_id)
        service_id = changes.get("service_id", appt.service_id)
        start = changes.get("start_time", appt.start_time)

        barber = self._barbers.get(barber_id)
        service = self._services.get(service_id)
        if not barber.is_active:
            raise HTTPException(400, "Barber is not active")
        end = start + timedelta(minutes=service.duration_minutes)
        self._ensure_barber_free(barber_id, start, end, exclude_id=appt.id)

        appt.barber_id, appt.service_id, appt.start_time, appt.end_time = barber_id, service_id, start, end
        if "notes" in changes:
            appt.notes = changes["notes"]
        self._db.commit()
        self._db.refresh(appt)
        return appt

    def set_status(self, appointment_id: int, status: str) -> Appointment:
        appt = self.get(appointment_id)
        if status == "completed":
            raise HTTPException(400, "Use POST /appointments/{id}/checkout to complete an appointment")
        if appt.status == "completed":
            raise HTTPException(400, "A completed appointment cannot be changed")
        appt.status = status
        self._db.commit()
        self._db.refresh(appt)
        return appt

    def delete(self, appointment_id: int) -> None:
        appt = self.get(appointment_id)
        if appt.payment:
            raise HTTPException(409, "Appointment has a payment record and cannot be deleted")
        self._db.delete(appt)
        self._db.commit()

    # ---------- availability (helps the receptionist/customer pick a time) ----------
    def free_slots(self, barber_id: int, service_id: int, on_date: date) -> list[dict]:
        barber = self._barbers.get(barber_id)
        service = self._services.get(service_id)
        if not barber.is_active:
            return []
        length = timedelta(minutes=service.duration_minutes)
        cursor = datetime.combine(on_date, OPEN_TIME)
        closing = datetime.combine(on_date, CLOSE_TIME)
        now = datetime.now()
        slots = []
        while cursor + length <= closing:
            if cursor >= now:
                try:
                    self._ensure_barber_free(barber_id, cursor, cursor + length)
                    slots.append({"start_time": cursor, "end_time": cursor + length})
                except HTTPException:
                    pass
            cursor += timedelta(minutes=SLOT_STEP)
        return slots


class BillingService:
    """Handles the payment transaction and sales reporting."""

    def __init__(self, db: Session):
        self._db = db
        self._appointments = AppointmentService(db)

    def checkout(self, appointment_id: int, method: str, amount_tendered: float):
        """TRANSACTION: record the payment AND mark the appointment completed.
        Both changes are saved together with one commit. If anything fails,
        rollback() undoes everything so the data never ends up half-updated."""
        appt = self._appointments.get(appointment_id)

        if appt.status == "cancelled":
            raise HTTPException(400, "Cannot check out a cancelled appointment")
        if appt.status == "completed" or appt.payment:
            raise HTTPException(409, "This appointment is already paid")

        price = appt.service.price
        if amount_tendered < price:
            raise HTTPException(400, f"Amount is not enough. Price is {price:.2f}")

        try:
            payment = Payment(appointment_id=appt.id, amount=price, method=method,
                              paid_at=datetime.now())
            self._db.add(payment)
            appt.status = "completed"
            self._db.commit()          # both changes saved together
        except Exception:
            self._db.rollback()        # or neither is saved
            raise HTTPException(500, "Payment failed. No changes were saved")

        self._db.refresh(appt)
        self._db.refresh(payment)
        return appt, payment, round(amount_tendered - price, 2)

    def daily_report(self, on_date: date) -> dict:
        day = datetime.combine(on_date, time.min)
        rows = self._db.execute(
            select(Barber.id, Barber.name,
                   func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0))
            .join(Appointment, Appointment.barber_id == Barber.id)
            .join(Payment, Payment.appointment_id == Appointment.id)
            .where(Payment.paid_at >= day, Payment.paid_at < day + timedelta(days=1))
            .group_by(Barber.id, Barber.name)
            .order_by(func.sum(Payment.amount).desc())
        ).all()
        by_barber = [{"barber_id": r[0], "barber_name": r[1],
                      "appointments_completed": r[2], "total_sales": float(r[3])} for r in rows]
        return {
            "date": on_date.isoformat(),
            "appointments_completed": sum(b["appointments_completed"] for b in by_barber),
            "total_sales": sum(b["total_sales"] for b in by_barber),
            "by_barber": by_barber,
        }
