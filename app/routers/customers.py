from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..repositories import CustomerRepository
from ..schemas import CustomerCreate, CustomerUpdate, CustomerOut

router = APIRouter(prefix="/customers", tags=["Customers"])


def repo(db: Session = Depends(get_db)) -> CustomerRepository:
    return CustomerRepository(db)


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(data: CustomerCreate, r: CustomerRepository = Depends(repo)):
    return r.create(data.model_dump())


@router.get("", response_model=list[CustomerOut])
def list_customers(search: str | None = None, r: CustomerRepository = Depends(repo)):
    return r.list(search=search)


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, r: CustomerRepository = Depends(repo)):
    return r.get(customer_id)


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, data: CustomerUpdate, r: CustomerRepository = Depends(repo)):
    return r.update(customer_id, data.model_dump(exclude_unset=True))


@router.delete("/{customer_id}", status_code=204)
def delete_customer(customer_id: int, r: CustomerRepository = Depends(repo)):
    r.delete(customer_id)
