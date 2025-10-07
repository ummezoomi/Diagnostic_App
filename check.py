# check.py
import streamlit as st
import medical_camp  # import your main app file (must be in same folder)

# --- Persistent session setup (shared across reruns & pages) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "username" not in st.session_state:
    st.session_state.username = ""

st.set_page_config(layout="centered", page_title="EMR Login")

# --- Hardcoded users and roles ---
USERS = {
    "admin": {"password": "12345", "role": "admin"},
    "doctor": {"password": "d1234", "role": "doctor"},
    "pharmacy": {"password": "p1234", "role": "pharmacy"}
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
    medical_camp.run_app()
    st.stop()



# --- If user is already logged in, skip login page ---
if st.session_state.get("logged_in", False):
    medical_camp.run_app()
    st.stop()  # prevent re-rendering login form below


# --- Helper info for testing ---
st.markdown("---")
st.write("**Login Credentials (for demo):**")
st.write("- 🧑‍💼 admin / 12345 → full access (all tabs)")
st.write("- 👨‍⚕️ doctor / d1234 → patient entry + records (edit allowed)")
st.write("- 💊 pharmacy / p1234 → pharmacy dispensation + patient records (view-only)")
