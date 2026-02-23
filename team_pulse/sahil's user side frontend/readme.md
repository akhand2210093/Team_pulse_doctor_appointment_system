### Sprint 0 Technical Design: Doctor Appointment System

This document outlines the strict technical architecture required to satisfy the provided problem statement. Present this during the design phase.

---

### 1. System Architecture & Tech Stack

* **Database:** MySQL (Strictly mandated by problem statement).
* **Backend:** FastAPI + SQLAlchemy ORM (Required for transactional reliability and concurrency handling).
* **Frontend:** Streamlit (For rapid dashboard development; strictly decoupled from backend).

---

### 2. Database Schema & Integrity Controls

The system relies on strict relational constraints to prevent data corruption.

* **`Specialty` Table:** `id` (PK), `name` (VARCHAR).
* **`Doctor` Table:** `id` (PK), `name` (VARCHAR), `specialty_id` (FK), `mode` (ENUM: 'Online', 'Offline'), `fee` (DECIMAL).
* **`Patient` Table:** `id` (PK), `name` (VARCHAR), `contact` (VARCHAR), `dob` (DATE), `email` (VARCHAR).
* **`DoctorSchedule` Table:** `id` (PK), `doctor_id` (FK), `schedule_date` (DATE), `time_slot` (TIME), `is_booked` (BOOLEAN).
* **Integrity Enforcement:** A `UNIQUE(doctor_id, schedule_date, time_slot)` constraint is applied at the database level to serve as the baseline defense against double-booking.


* **`Appointment` Table:** `id` (PK), `patient_id` (FK), `doctor_id` (FK), `schedule_id` (FK), `status` (ENUM: confirmed, completed, cancelled, no-show), `artifact` (VARCHAR - stores video link or clinic address).

---

### 3. API Specification & Business Logic

| Endpoint | Method | Purpose | Failure Handling |
| --- | --- | --- | --- |
| `/api/doctors` | GET | List doctors filtered by `mode` and `specialty`. | Returns empty list if no match. |
| `/api/appointments` | POST | Books appointment. Enforces mode-doctor match via Pydantic validation before DB insertion. | 422 Unprocessable Entity if mode mismatch. 409 Conflict if slot locked. |
| `/api/appointments/{id}` | PATCH | Updates appointment status lifecycle. | 404 Not Found if ID invalid. |
| `/api/reports/daily` | GET | Aggregates appointments and revenue by mode/specialty. | Returns 0 for empty groupings. |

**Concurrency Resolution (The Double-Booking Fix):**
The `POST /api/appointments` endpoint implements a **Pessimistic Read/Write Lock**. The SQLAlchemy transaction executes `SELECT ... FOR UPDATE` on the `DoctorSchedule` row. Concurrent booking attempts for the same slot will queue or fail instantly, guaranteeing zero double-bookings under heavy API load.

---

### 4. Stretch Goals (Differentiation Factor)

Executing these features is high-risk. Attempt them **only** after the core CRUD APIs, MySQL schemas, and Streamlit frontend are fully functional and pass the Acceptance Criteria.

* **Teleconsultation (Baseline vs. Stretch):**
* *Baseline:* Generate a static placeholder string (e.g., `https://telemed.local/room/123`) in the `artifact` column for Online bookings. This satisfies the strict wording of the problem statement.
* *Stretch (LiveKit):* Deploy a headless LiveKit Python worker. Upon booking an 'Online' appointment, the API generates a live WebRTC room token and stores it in the `artifact` column. Do not attempt frontend UI integration; demonstrate the connection via the LiveKit Agent Playground.


* **Notification System (WhatsApp):**
* *Execution:* Integrate the Whatsmeow library. Upon a successful database commit in the booking API, trigger an asynchronous background task in FastAPI to send the booking artifact (clinic address or video link) directly to the patient's phone number.



---

Would you like the exact SQLAlchemy code snippet that implements the `SELECT FOR UPDATE` pessimistic lock for the booking endpoint?

Current time is Monday, February 23, 2026 at 12:16:35 PM IST.