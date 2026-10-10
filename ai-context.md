# Project context
Barbershop appointment, payment and sales backend. Stack: Python, FastAPI, SQLAlchemy 2.0, SQLite, Pydantic v2.
- `main.py`: app entry, creates tables, seeds services
- `app/models.py`: Customer, Barber, Service, Appointment, Payment
- `app/schemas.py`: request/response validation
- `app/repositories.py`: OOP CRUD (BaseRepository + one subclass per table)
- `app/services.py`: AppointmentService (booking, availability), BillingService (checkout transaction, daily report)
- `app/routers/`: thin endpoints that call the classes
Rules: no overlapping appointments for a barber; an appointment becomes `completed` only through checkout, which saves the payment and status change in one transaction.
