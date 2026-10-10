# Barbershop Appointment and Management System

A FastAPI + SQLite backend for a barbershop that handles booking, schedule conflicts, payment and daily sales.

## Problem
Small barbershops usually take bookings through messages or a paper logbook. This causes:
- double-booked barbers and customers who arrive to find no free barber,
- no quick way to see which times a barber is free,
- payments written on paper, so daily sales and each barber's earnings are counted by hand and often wrong.

## Solution and intended users
| User | What they do in the system |
|---|---|
| Receptionist / owner | Register customers and barbers, book and reschedule appointments, check free time slots, check out and receive payment |
| Barber | Has appointments listed by date (`GET /appointments?barber_id=1&on_date=...`) |
| Owner | Reads the daily sales report per barber |

## Main workflow
1. **Book**: pick customer, barber, service and time. The end time is computed from the service duration. The system rejects overlapping bookings, past dates and inactive barbers.
2. **Check availability**: `GET /barbers/{id}/availability` lists the free start times for the day (shop hours 9:00 to 19:00).
3. **Checkout (transaction)**: `POST /appointments/{id}/checkout` records the payment and marks the appointment completed in one database transaction. If either step fails, both are rolled back. It also rejects insufficient cash and double payment, and returns the change.
4. **Report**: `GET /reports/daily?on_date=...` gives completed appointments and total sales per barber.

## Database (SQLite, 5 related tables)
```
customers 1---* appointments *---1 barbers
                    |  *---1 services
                    1
                    |
                    1
                 payments
```
Every table has a primary key. `appointments` holds foreign keys to customers, barbers and services. `payments.appointment_id` is a unique foreign key (one payment per appointment). Deleting a record that other records depend on is blocked (HTTP 409).

## OOP design
| File | Classes | Concept |
|---|---|---|
| `app/models.py` | `Customer`, `Barber`, `Service`, `Appointment`, `Payment` | Classes mapped to tables, relationships between objects |
| `app/repositories.py` | `BaseRepository` and `CustomerRepository`, `BarberRepository`, `ServiceRepository` | Inheritance (shared CRUD), polymorphism (children override `search`, `before_create`, `delete_guard`), encapsulation (private `_db`) |
| `app/services.py` | `AppointmentService`, `BillingService` | Each class owns one set of business rules; composition (services use repositories) |
| `app/routers/` | functions only | Thin API layer that calls the classes |

## Project structure
```
main.py                 app entry, creates tables, seeds services
app/database.py         engine, session
app/models.py           tables
app/schemas.py          request/response validation
app/repositories.py     CRUD classes
app/services.py         booking and billing classes
app/routers/            API endpoints
```

## Run
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows  (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn main:app --reload
```
Open http://127.0.0.1:8000/docs. The `barbershop.db` file is created automatically (open it with the SQLite Viewer extension).

## Quick test order (in /docs)
1. `POST /barbers` `{"name": "Mark"}`
2. `POST /customers` `{"name": "Juan", "phone": "09171234567"}`
3. `GET /barbers/1/availability?service_id=1&on_date=<tomorrow>`
4. `POST /appointments` with a free start time
5. `POST /appointments/1/checkout` `{"method": "cash", "amount_tendered": 200}`
6. `GET /reports/daily?on_date=<today>`

## Endpoints
- `/customers`, `/barbers`, `/services`: full CRUD (customers searchable by name or phone)
- `/appointments`: book, list (filter by `barber_id`, `customer_id`, `on_date`, `status`), reschedule, delete
- `PATCH /appointments/{id}/status`: pending, confirmed or cancelled
- `POST /appointments/{id}/checkout`: payment transaction
- `GET /barbers/{id}/availability`: free time slots
- `GET /reports/daily`: sales report
