import streamlit as st
import datetime
import requests

st.set_page_config(page_title="Login")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "role" not in st.session_state:
    st.session_state.role = None


if not st.session_state.logged_in:

    st.title("Login")

    username = st.text_input("Username")
    contact = st.text_input("Contact Number")
    email = st.text_input("Email id") 
    dob = st.date_input("Enter your Date of Birth", min_value=datetime.date(1900, 1, 1))

    role = st.selectbox("Select your role:", ["Patient", "Staff"])

    if st.button("Login", use_container_width=True):

        payload = {
            "name": username,
            "contact": contact,
            "dob": str(dob),
            "email": email
        }

        try:
            response = requests.post(
                "https://sturdier-tamra-venally.ngrok-free.dev/api/patients/",
                json=payload,
                headers={"ngrok-skip-browser-warning": "true"}   
            )

            if response.status_code in [200, 201]:

                st.session_state.logged_in = True
                st.session_state.role = role

                st.success("Login successful")

                if role == "Staff":
                    st.switch_page("pages/staff_dashboard.py")

                elif role == "Patient":
                    st.markdown(
                        """
                        <meta http-equiv="refresh" content="0; url=https://8efb-117-55-241-39.ngrok-free.app">
                        """,
                        unsafe_allow_html=True)

            else:
                st.error(f"Failed Status Code: {response.status_code}")
                st.write(response.text)

        except Exception as e:
            st.error("API connection failed")
            st.write(str(e))

 