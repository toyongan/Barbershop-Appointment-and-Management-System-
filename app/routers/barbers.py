from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..repositories import BarberRepository
from ..services import AppointmentService
from ..schemas import BarberCreate, BarberUpdate, BarberOut, Slot

router = APIRouter(prefix="/barbers", tags=["Barbers"])


def repo(db: Session = Depends(get_db)) -> BarberRepository:
    return BarberRepository(db)


@router.post("", response_model=BarberOut, status_code=201)
def create_barber(data: BarberCreate, r: BarberRepository = Depends(repo)):
    return r.create(data.model_dump())


@router.get("", response_model=list[BarberOut])
def list_barbers(active_only: bool = False, r: BarberRepository = Depends(repo)):
    return r.list(active_only=active_only)


@router.get("/{barber_id}", response_model=BarberOut)
def get_barber(barber_id: int, r: BarberRepository = Depends(repo)):
    return r.get(barber_id)


@router.get("/{barber_id}/availability", response_model=list[Slot])
def barber_availability(barber_id: int, service_id: int, on_date: date,
                        db: Session = Depends(get_db)):
    """Free start times for a barber on a date, for the chosen service."""
    return AppointmentService(db).free_slots(barber_id, service_id, on_date)


@router.put("/{barber_id}", response_model=BarberOut)
def update_barber(barber_id: int, data: BarberUpdate, r: BarberRepository = Depends(repo)):
    return r.update(barber_id, data.model_dump(exclude_unset=True))


@router.delete("/{barber_id}", status_code=204)
def delete_barber(barber_id: int, r: BarberRepository = Depends(repo)):
    r.delete(barber_id)
