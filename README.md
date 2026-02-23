# Doctor Appointment System

This project is a comprehensive appointment booking system designed to manage doctors, patients, schedules, and appointments. The backend is built using **Django REST Framework (DRF)**, providing robust API endpoints, while the frontend is built using **Streamlit** for a simple and interactive user interface.

---

## 🚀 Features

* **Specialty & Doctor Management:** Categorize doctors by their medical specialties and specify their consultation mode (Online or Offline).
* **Smart Scheduling:** Doctors can have designated time slots for specific dates. The system automatically filters out booked slots to prevent double-booking.
* **Appointment Booking & Validation:** Patients can book available slots. The system validates that the selected consultation mode matches the doctor's designated mode and ensures the slot is still open.
* **Automated Slot Locking:** Once an appointment is successfully created, the associated time slot is immediately marked as booked (`is_booked = True`).
* **Daily Analytics:** A dedicated summary endpoint provides real-time tracking of today's total completed appointments and generated revenue, grouped by consultation mode.

---

## 🔄 Data Flow & Application Structure

The application follows a structured flow to ensure smooth operations between the Streamlit frontend and the DRF backend:

1. **Setup (Admin/Staff):**
   * Create `Specialty` categories.
   * Add `Doctor` profiles, assigning them a specialty, mode (online/offline), and consultation fee.
   * Generate `DoctorSchedule` entries (time slots) for doctors on specific dates.
2. **Browsing (Patient/User):**
   * The Streamlit frontend queries the `/doctors/` API. Users can filter doctors by specialty or mode.
   * Upon selecting a doctor, the frontend queries the `/schedules/` API to fetch only the **available** (unbooked) time slots for that specific doctor.
3. **Booking an Appointment:**
   * The user creates an `Appointment` via the Streamlit interface, providing patient details, the selected doctor, the schedule, and the mode.
   * The backend validates the request. If successful, the `DoctorSchedule` is automatically locked.
4. **Analytics:**
   * Clinic administrators can view a dashboard in Streamlit that fetches data from the `/daily-summary/` API, showing revenue and patient footfall for the current day.

---

## 📡 API Endpoints

The backend exposes the following RESTful API endpoints. 

### Core Resources

| Endpoint | Methods | Description | Query Parameters / Filters |
| :--- | :--- | :--- | :--- |
| `/specialties/` | GET, POST, PUT, DELETE | Manage medical specialties. | None |
| `/doctors/` | GET, POST, PUT, DELETE | Manage doctors. Returns only `active` doctors. | `?mode=` (online/offline)<br>`?specialty=` (specialty_id) |
| `/patients/` | GET, POST, PUT, DELETE | Manage patient records. | None |
| `/schedules/` | GET, POST, PUT, DELETE | Manage time slots. Returns only unbooked slots. | `?doctor=` (doctor_id)<br>`?date=` (YYYY-MM-DD) |
| `/appointments/` | GET, POST, PUT, DELETE | Manage appointments. Auto-locks schedules on POST. | None |

### Custom Endpoints

| Endpoint | Methods | Description |
| :--- | :--- | :--- |
| `/daily-summary/` | GET | Returns total appointments and revenue for today, grouped by consultation mode (only counts `completed` appointments). |

---

## 🛠️ Tech Stack

* **Backend:** Django, Django REST Framework (DRF)
* **Frontend:** Streamlit
* **Database:** Postgres (can be configured to SQLite/MySQL)

---

## 💻 Local Development Setup

Follow these steps to run the project locally.

### 1. Backend Setup (Django)

1. Clone the repository and navigate to the backend directory.
2. Create and activate a virtual environment.
3. Install the required dependencies:
   ```bash
   pip install django djangorestframework
Apply database migrations:

Bash
python manage.py makemigrations
python manage.py migrate
Run the development server:

Bash
python manage.py runserver
The API will be available at http://localhost:8000/

2. Frontend Setup (Streamlit)
Open a new terminal window and navigate to your frontend directory.

Install Streamlit:

Bash
pip install streamlit requests
Run the Streamlit application:

Bash
streamlit run app.py
The Streamlit interface will open in your default browser, typically at http://localhost:8501/
