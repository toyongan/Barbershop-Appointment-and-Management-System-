from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, SessionLocal
from app import models
from app.routers import customers, barbers, services, appointments, reports


def seed_defaults():
    """Add a few starter services the first time the app runs."""
    with SessionLocal() as db:
        if db.query(models.Service).count() == 0:
            db.add_all([
                models.Service(name="Haircut", price=150, duration_minutes=30),
                models.Service(name="Beard Trim", price=100, duration_minutes=20),
                models.Service(name="Haircut + Beard", price=220, duration_minutes=45),
                models.Service(name="Shave", price=120, duration_minutes=25),
            ])
            db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_defaults()
    yield


app = FastAPI(title="Barbershop API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customers.router)
app.include_router(barbers.router)
app.include_router(services.router)
app.include_router(appointments.router)
app.include_router(reports.router)


@app.get("/", tags=["Health"])
def root():
    return {"message": "Barbershop API is running", "docs": "/docs"}
