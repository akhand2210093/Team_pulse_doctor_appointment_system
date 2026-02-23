import streamlit as st
import uuid
from datetime import time


st.title("Staff Dashboard")

if "patient_uuid" not in st.session_state:
    st.session_state.patient_uuid = ""

def generate_uuid():
    st.session_state.patient_uuid = str(uuid.uuid4  ())

name = st.text_input("Patient Name")

col1, col2 = st.columns([3, 1])

with col1:
    st.text_input(
        "Patient UUID",
        value=st.session_state.patient_uuid,
        disabled=True
    )

with col2:
    st.button("Generate", on_click=generate_uuid)


history = st.text_area("Patient History")


st.subheader("Appointment Details")

col3, col4 = st.columns(2)

with col3:
    appointment_date = st.date_input("Select Date")

with col4:
    appointment_time = st.time_input("Select Time", value=time(9, 0))

mode = st.selectbox("Mode", ["Online", "Offline"])

doctor = st.selectbox(
    "Doctor",
    ["Dr. Sharma", "Dr. Mehta", "Dr. Khan", "Dr. Verma"]
)

speciality = st.selectbox(
    "Speciality",
    ["Cardiology", "Dermatology", "Neurology", "Orthopedics", "General Physician"]
)

if st.button("Book Appointment"):

    if not st.session_state.patient_uuid:
        st.error("Please generate Patient UUID first.")
    else:
        st.success("Appointment Booked Successfully!")

        st.write("### Booking Summary")
        st.write("Name:", name)
        st.write("UUID:", st.session_state.patient_uuid)
        st.write("History:", history)
        st.write("Date:", appointment_date)
        st.write("Time:", appointment_time)
        st.write("Mode:", mode)
        st.write("Speciality:", speciality)
        st.write("Doctor:", doctor)

# import streamlit as st
# import uuid
# import requests
# from datetime import time

# st.title("Staff Dashboard")

# API_URL = "https://hcl-das-backend.onrender.com/api/doctors/"  # Change to your API



# def fetch_doctors():
#     try:
#         response = requests.get(API_URL)
#         print(response.json())
#         if response.status_code == 200:
#             print(response.json())
#             return response.json()
#         else:
#             return []
#     except:
#         return []

# doctors_data = fetch_doctors()
# print("HEY:::::", doctors_data)


# if "patient_uuid" not in st.session_state:
#     st.session_state.patient_uuid = ""

# def generate_uuid():
#     st.session_state.patient_uuid = str(uuid.uuid4())


# name = st.text_input("Patient Name")


# col1, col2 = st.columns([3, 1])

# with col1:
#     st.text_input(
#         "Patient UUID",
#         value=st.session_state.patient_uuid,
#         disabled=True
#     )

# with col2:
#     st.button("Generate", on_click=generate_uuid)


# history = st.text_area("Patient History")

# st.subheader("Appointment Details")

# col3, col4 = st.columns(2)

# with col3:
#     appointment_date = st.date_input("Select Date")

# with col4:
#     appointment_time = st.time_input("Select Time", value=time(9, 0))


# active_doctors = [doc for doc in doctors_data if doc["active"]]


# mode = st.selectbox("Mode", ["Online", "Offline"])


# specialities = sorted(list(set(doc["specialty"] for doc in active_doctors)))

# if specialities:
#     speciality = st.selectbox("Speciality", specialities)
# else:
#     speciality = None
#     st.warning("No active doctors available.")


# filtered_doctors = [
#     doc for doc in active_doctors
#     if doc["mode"] == mode and doc["specialty"] == speciality
# ]


# if filtered_doctors:
#     doctor_map = {
#         f"{doc['name']} (₹{doc['fee']})": doc
#         for doc in filtered_doctors
#     }

#     selected_label = st.selectbox("Doctor", list(doctor_map.keys()))
#     selected_doctor = doctor_map[selected_label]
# else:
#     selected_doctor = None
#     st.warning("No doctors match selected criteria.")


# if st.button("Book Appointment"):

#     if not st.session_state.patient_uuid:
#         st.error("Please generate Patient UUID first.")
#     elif not selected_doctor:
#         st.error("Please select a valid doctor.")
#     else:
#         st.success("Appointment Booked Successfully!")

#         st.write("### Booking Summary")
#         st.write("Name:", name)
#         st.write("UUID:", st.session_state.patient_uuid)
#         st.write("History:", history)
#         st.write("Date:", appointment_date)
#         st.write("Time:", appointment_time)
#         st.write("Mode:", mode)
#         st.write("Speciality:", speciality)
#         st.write("Doctor:", selected_doctor["name"])
#         st.write("Fee:", selected_doctor["fee"])