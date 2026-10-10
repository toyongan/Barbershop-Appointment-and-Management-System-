from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field

Status = Literal["pending", "confirmed", "completed", "cancelled"]


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Customer ----------
class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=5, max_length=30)
    email: EmailStr | None = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None


class CustomerOut(CustomerBase, ORMBase):
    id: int


# ---------- Barber ----------
class BarberBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str | None = None
    is_active: bool = True


class BarberCreate(BarberBase):
    pass


class BarberUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    is_active: bool | None = None


class BarberOut(BarberBase, ORMBase):
    id: int


# ---------- Service ----------
class ServiceBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(ge=0)
    duration_minutes: int = Field(default=30, gt=0, le=480)


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: str | None = None
    price: float | None = Field(default=None, ge=0)
    duration_minutes: int | None = Field(default=None, gt=0, le=480)


class ServiceOut(ServiceBase, ORMBase):
    id: int


# ---------- Appointment ----------
class AppointmentCreate(BaseModel):
    customer_id: int
    barber_id: int
    service_id: int
    start_time: datetime
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    barber_id: int | None = None
    service_id: int | None = None
    start_time: datetime | None = None
    notes: str | None = None


class StatusUpdate(BaseModel):
    status: Status


class AppointmentOut(ORMBase):
    id: int
    customer_id: int
    barber_id: int
    service_id: int
    start_time: datetime
    end_time: datetime
    status: Status
    notes: str | None = None
    customer: CustomerOut
    barber: BarberOut
    service: ServiceOut


# ---------- Payment / Checkout ----------
PaymentMethod = Literal["cash", "gcash", "card"]


class CheckoutRequest(BaseModel):
    method: PaymentMethod = "cash"
    amount_tendered: float = Field(gt=0, description="Amount handed over by the customer")


class PaymentOut(ORMBase):
    id: int
    appointment_id: int
    amount: float
    method: PaymentMethod
    paid_at: datetime


class CheckoutOut(BaseModel):
    appointment: AppointmentOut
    payment: PaymentOut
    change: float


class BarberSales(BaseModel):
    barber_id: int
    barber_name: str
    appointments_completed: int
    total_sales: float


class DailyReport(BaseModel):
    date: str
    appointments_completed: int
    total_sales: float
    by_barber: list[BarberSales]


class Slot(BaseModel):
    start_time: datetime
    end_time: datetime
