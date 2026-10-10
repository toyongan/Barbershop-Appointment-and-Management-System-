from __future__ import annotations
"""Repository classes: each one is responsible for the database access of ONE table.

OOP concepts used here:
- Abstraction / Inheritance: BaseRepository holds the generic CRUD, child classes inherit it.
- Encapsulation: the SQLAlchemy session is kept private inside the object (self._db).
- Polymorphism: child classes override `search` or `delete_guard` with their own rules.
"""
from typing import Generic, TypeVar
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Customer, Barber, Service, Appointment

T = TypeVar("T")


class BaseRepository(Generic[T]):
    model: type[T]
    label: str = "Record"

    def __init__(self, db: Session):
        self._db = db

    # ---- Create ----
    def create(self, data: dict) -> T:
        self.before_create(data)
        obj = self.model(**data)
        self._db.add(obj)
        self._db.commit()
        self._db.refresh(obj)
        return obj

    # ---- Read ----
    def get(self, obj_id: int) -> T:
        obj = self._db.get(self.model, obj_id)
        if not obj:
            raise HTTPException(404, f"{self.label} not found")
        return obj

    def list(self, **filters) -> list[T]:
        return list(self._db.scalars(self.search(**filters)).all())

    def search(self, **filters):
        return select(self.model)

    # ---- Update ----
    def update(self, obj_id: int, data: dict) -> T:
        obj = self.get(obj_id)
        for key, value in data.items():
            setattr(obj, key, value)
        self._db.commit()
        self._db.refresh(obj)
        return obj

    # ---- Delete ----
    def delete(self, obj_id: int) -> None:
        obj = self.get(obj_id)
        self.delete_guard(obj_id)
        self._db.delete(obj)
        self._db.commit()

    # ---- Hooks that child classes can override ----
    def before_create(self, data: dict) -> None:
        pass

    def delete_guard(self, obj_id: int) -> None:
        pass


class CustomerRepository(BaseRepository[Customer]):
    model = Customer
    label = "Customer"

    def search(self, search: str | None = None, **_):
        stmt = select(Customer).order_by(Customer.name)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(Customer.name.ilike(like) | Customer.phone.ilike(like))
        return stmt

    def before_create(self, data: dict) -> None:
        if self._db.scalar(select(Customer).where(Customer.phone == data["phone"])):
            raise HTTPException(409, "A customer with this phone already exists")

    def delete_guard(self, obj_id: int) -> None:
        if self._db.scalar(select(Appointment.id).where(Appointment.customer_id == obj_id)):
            raise HTTPException(409, "Customer has appointments and cannot be deleted")


class BarberRepository(BaseRepository[Barber]):
    model = Barber
    label = "Barber"

    def search(self, active_only: bool = False, **_):
        stmt = select(Barber).order_by(Barber.name)
        if active_only:
            stmt = stmt.where(Barber.is_active.is_(True))
        return stmt

    def delete_guard(self, obj_id: int) -> None:
        if self._db.scalar(select(Appointment.id).where(Appointment.barber_id == obj_id)):
            raise HTTPException(409, "Barber has appointments. Deactivate instead (is_active=false)")


class ServiceRepository(BaseRepository[Service]):
    model = Service
    label = "Service"

    def search(self, **_):
        return select(Service).order_by(Service.name)

    def before_create(self, data: dict) -> None:
        if self._db.scalar(select(Service).where(Service.name == data["name"])):
            raise HTTPException(409, "Service name already exists")

    def delete_guard(self, obj_id: int) -> None:
        if self._db.scalar(select(Appointment.id).where(Appointment.service_id == obj_id)):
            raise HTTPException(409, "Service is used by appointments and cannot be deleted")
