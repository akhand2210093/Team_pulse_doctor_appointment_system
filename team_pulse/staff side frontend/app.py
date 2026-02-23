import streamlit as st
import datetime
import requests

st.set_page_config(
    page_title="Login",
)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "role" not in st.session_state:
    st.session_state.role = None


st.markdown("""
    <style>
        .main {
            background-color: #f5f7fa;
        }
       
        .stButton>button {
            border-radius: 10px;
            height: 45px;
            width: 100%;
            background: linear-gradient(90deg, #4b6cb7, #182848);
            color: white;
            font-weight: 600;
            border: none;
        }
            
        .title {
            text-align: center;
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 30px;
        }
        
    </style>
""", unsafe_allow_html=True)

if not st.session_state.logged_in:

    st.title("Login")
    st.html('<div class="title">Welcome Back, Hi</div>')

    username = st.text_input("Username")
    contact = st.text_input("Contact Number")
    email = st.text_input("Email id") 
    dob = st.date_input("Enter your Date of Birth", min_value=datetime.date(1900, 1, 1))

    role = st.selectbox(
        "Select your role:",
        ["Patient", "Staff"]
    )

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        login_clicked = st.button("Login", use_container_width=True)
        payload = {
                "name": username,
                "contact": contact,
                "dob": str(dob),
                "email": email
            }

        if login_clicked:
            try:
                response = requests.post(
                    "https://hcl-das-backend.onrender.com/api/patients/",
                    json=payload
                )
                print(response)
                if response.status_code in [200, 201]:
                    st.success("Data submitted successfully")
                    st.write(response.json())
                    if role == "Staff":
                        st.switch_page("pages/staff_dashboard.py")
                    if role == "Patient":
                        st.markdown(
                            """
                            <script>
                                window.location.href = "https://8efb-117-55-241-39.ngrok-free.app";
                            </script>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.error(f"Failed Status Code: {response.status_code}")
                    st.write(response.text)

            except Exception as e:
                st.error("API connection failed ")
                st.write(str(e))

else:
    print(st.session_state.role)
    if st.session_state.role == "Staff":
        st.title("Staff Dashboard")
        st.write("Welcome to Staff Panel")