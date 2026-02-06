# check.py
import streamlit as st
import medical_camp  # Ensure medical_camp.py is in the same folder
import registration  # Ensure registration.py is in the same folder

# --- Persistent session setup ---
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

# =========================================================
# 1. AUTO-LOGIN LOGIC (Check URL on Refresh)
# =========================================================
if not st.session_state["logged_in"]:
    qp = st.query_params  # Get URL parameters

    # If URL has credentials, try to auto-login
    if "role" in qp and "username" in qp:
        u_name = qp["username"]
        u_role = qp["role"]

        # Security check: verify the role matches your hardcoded list
        if u_name in USERS and USERS[u_name]["role"] == u_role:
            st.session_state["logged_in"] = True
            st.session_state["role"] = u_role
            st.session_state["username"] = u_name
            st.rerun()

# =========================================================
# 2. LOGIN FORM (Only show if not logged in)
# =========================================================
if not st.session_state["logged_in"]:
    st.title("🔒 Medical Camp EMR — Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if username in USERS and USERS[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.role = USERS[username]["role"]
            st.session_state.username = username

            # --- SAVE TO URL FOR PERSISTENCE ---
            st.query_params["role"] = USERS[username]["role"]
            st.query_params["username"] = username

            st.success(f"Welcome, {username}! Role: {st.session_state['role']}")
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

# =========================================================
# 3. ROUTING LOGIC (If logged in, run the app)
# =========================================================
if st.session_state.get("logged_in", False):
    role = st.session_state["role"]

    # Add a global logout button in the sidebar
    # This acts as a "Hard Logout" that clears the URL too
    if st.sidebar.button("Logout", key="main_app_logout"):
        st.session_state.clear()
        st.query_params.clear() # Clear URL so refresh doesn't auto-login
        st.rerun()

    # ADMIN
    if role == "admin":
        medical_camp.run_app()

    # DOCTOR
    elif role == "doctor":
        medical_camp.run_app()

    # PHARMACY
    elif role == "pharmacy":
        medical_camp.run_app()

    # REGISTRATION STAFF
    elif role == "registration":
        registration.run_registration()

#streamlit run check.py --server.port 8501 --server.enableCORS true --server.enableXsrfProtection false