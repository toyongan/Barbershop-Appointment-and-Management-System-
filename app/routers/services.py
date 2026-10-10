from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..repositories import ServiceRepository
from ..schemas import ServiceCreate, ServiceUpdate, ServiceOut

router = APIRouter(prefix="/services", tags=["Services"])


def repo(db: Session = Depends(get_db)) -> ServiceRepository:
    return ServiceRepository(db)


@router.post("", response_model=ServiceOut, status_code=201)
def create_service(data: ServiceCreate, r: ServiceRepository = Depends(repo)):
    return r.create(data.model_dump())


@router.get("", response_model=list[ServiceOut])
def list_services(r: ServiceRepository = Depends(repo)):
    return r.list()


@router.get("/{service_id}", response_model=ServiceOut)
def get_service(service_id: int, r: ServiceRepository = Depends(repo)):
    return r.get(service_id)


@router.put("/{service_id}", response_model=ServiceOut)
def update_service(service_id: int, data: ServiceUpdate, r: ServiceRepository = Depends(repo)):
    return r.update(service_id, data.model_dump(exclude_unset=True))


@router.delete("/{service_id}", status_code=204)
def delete_service(service_id: int, r: ServiceRepository = Depends(repo)):
    r.delete(service_id)
