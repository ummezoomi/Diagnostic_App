# check.py

import streamlit as st
import medical_camp  # import your main app file (must be in same folder)
import registration
# --- Persistent session setup (shared across reruns & pages) ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "role" not in st.session_state:
    st.session_state["role"] = ""
if "username" not in st.session_state:
    st.session_state["username"] = ""

st.set_page_config(layout="centered", page_title="EMR Login")

# --- Hardcoded users and roles ---
USERS = {
    "admin": {"password": "admin", "role": "admin"},
    "doctor": {"password": "d1234", "role": "doctor"},
    "pharmacy": {"password": "p1234", "role": "pharmacy"},
    "registration": {"password": "r1234", "role": "registration"}
}

# --- Login UI ---
st.title("🔒 Medical Camp EMR — Login")

with st.form("login_form"):
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Login")

# --- Login logic ---
if submitted:
    if username in USERS and USERS[username]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.role = USERS[username]["role"]
        st.session_state.username = username
        st.success(f"Welcome, {username}! Role: {st.session_state['role']}")
        st.rerun()  # rerun to go directly into the main app
    else:
        st.error("❌ Invalid username or password")

if st.session_state.get("logged_in", False):
    role = st.session_state["role"]

    # ADMIN
    if role == "admin":
        st.success("👑 Admin access granted — full system access.")
        medical_camp.run_app()

    # DOCTOR
    elif role == "doctor":
        st.success("👨‍⚕️ Doctor access granted — EMR only.")
        medical_camp.run_app()

    # PHARMACY
    elif role == "pharmacy":
        st.success("💊 Pharmacy access granted — EMR (view only).")
        medical_camp.run_app()

    # REGISTRATION STAFF
    elif role == "registration":
        st.success("📝 Registration access granted — patient registration only.")
        registration.run_registration()

    st.stop()






# --- If user is already logged in, skip login page ---
if st.session_state.get("logged_in", False):
    medical_camp.run_app()
    st.stop()  # prevent re-rendering login form below


# --- Helper info for testing ---
st.markdown("---")
st.write("**Login Credentials (for demo):**")
st.write("- 👨‍⚕️ doctor / d1234 → patient entry + records (edit allowed)")
st.write("- 💊 pharmacy / p1234 → pharmacy dispensation + patient records (view-only)")
st.write("- registration / r1234 -> Register and  view only")

#streamlit run check.py --server.port 8501 --server.enableCORS true --server.enableXsrfProtection false