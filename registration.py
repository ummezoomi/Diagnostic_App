# registration.py
import streamlit as st
import mysql.connector
import pandas as pd
import os
from mysql.connector.pooling import MySQLConnectionPool
import re
DB_FILE = "emr.db"

# ------------------- Input Validation Helper -------------------
# ------------------- Input Validation Helper -------------------
def validate_patient_inputs(name, cnic, nationality, address, phone, gender, age):
    """
    Validate and auto-clean patient registration inputs.
    Returns (True, "cleaned_cnic") if valid, else (False, "error message").
    """

    # --- Basic cleanup ---
    name = name.strip().title()
    cnic = cnic.strip().replace("-", "").replace(" ", "")
    nationality = nationality.strip().title()
    address = address.strip()
    phone = phone.strip()
    gender = gender.strip()

    # --- Name: alphabetic only (spaces allowed) ---
    if not name or not re.match(r"^[A-Za-z\s]+$", name):
        return False, "Patient name must contain only letters and spaces."

    # --- CNIC: digits only, must be 13 digits ---
    if not cnic.isdigit():
        return False, "CNIC must contain digits only."
    if len(cnic) != 13:
        return False, "CNIC must be exactly 13 digits long."

    # Auto-format CNIC to XXXXX-XXXXXXX-X
    formatted_cnic = f"{cnic[:5]}-{cnic[5:12]}-{cnic[12:]}"

    # --- Nationality: letters only (optional) ---
    if nationality and not re.match(r"^[A-Za-z\s]+$", nationality):
        return False, "Nationality must contain only letters and spaces."

    # --- Address: reasonable length ---
    if address and len(address) < 5:
        return False, "Address seems too short. Please enter a complete address."

    # --- Phone: digits + optional '+' allowed ---
    if phone and not re.match(r"^[0-9+]+$", phone):
        return False, "Phone number must contain only digits (and '+' if international)."
    if phone and len(phone) < 7:
        return False, "Phone number is too short."

    # --- Gender: must be selected ---
    if gender not in ["Male", "Female", "Other"]:
        return False, "Please select a valid gender."

    # --- Age: must be within range ---
    if not isinstance(age, int) or age <= 0 or age > 120:
        return False, "Age must be a valid integer between 1 and 120."

    return True, formatted_cnic

# Initialize a pool (do this globally, outside the function)
db_config = {
    "host": "localhost",
    "user": "root",
    "port": 3306,
    "password": "umerEMR123@",
    "database": "emr_system",
    "connection_timeout": 5
}


def get_connection():
    try:
        # Just create a fresh connection. It's fast and reliable.
        return mysql.connector.connect(**db_config)
    except Exception as e:
        st.error(f"MySQL connection failed: {e}")
        st.stop()

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        patient_id INT AUTO_INCREMENT PRIMARY KEY,
        patient_name VARCHAR(255),
        cnic VARCHAR(20) UNIQUE,
        nationality VARCHAR(100),
        address TEXT,
        phone VARCHAR(20),
        gender VARCHAR(10),
        age INT
    ) ENGINE=InnoDB;
    """)
    conn.commit()
    conn.close()

def run_registration():
    # Ensure DB exists
    init_db()

    # Prevent showing login form again
    if not st.session_state.get("logged_in", False):
        st.warning("Please login to access this page.")
        st.stop()

    # Only allow registration or admin
    role = st.session_state.get("role", "")
    if role not in ["registration", "admin"]:
        st.error("You do not have permission to access patient registration.")
        st.stop()

    # Page settings
    st.set_page_config(layout="centered", page_title="Patient Registration")
    st.title("🧾 Patient Registration")

    with st.form("reg_form", clear_on_submit=False):
        name = st.text_input("Patient Name")
        cnic = st.text_input("CNIC")
        nationality = st.text_input("Nationality")
        address = st.text_area("Address")
        phone = st.text_input("Phone Number")
        gender = st.selectbox("Gender", ["", "Male", "Female", "Other"])
        age = st.number_input("Age", min_value=0, max_value=120, step=1, value=0)

        submitted = st.form_submit_button("Register / Update Patient")

    if submitted:
        if not name.strip() or not cnic.strip():
            st.warning("Please provide at least Patient Name and CNIC.")
        else:
            # Run input validation
            is_valid, result = validate_patient_inputs(
                name,
                cnic,
                nationality,
                address,
                phone,
                gender,
                int(age)
            )

            if not is_valid:
                st.error(f"❌ Validation failed: {result}")
                st.stop()
            else:
                cnic = result

            conn = get_connection()
            c = conn.cursor()

            c.execute("SELECT patient_id FROM patients WHERE cnic=%s", (cnic.strip(),))
            existing = c.fetchone()
            if existing:
                c.execute("""
                    UPDATE patients
                    SET patient_name=%s, nationality=%s, address=%s, phone=%s, gender=%s, age=%s
                    WHERE cnic=%s
                """, (name.strip(), nationality.strip(), address.strip(), phone.strip(), gender, int(age), cnic.strip()))
                st.success(f"Updated patient (CNIC: {cnic}).")
            else:
                c.execute("""
                    INSERT INTO patients (patient_name, cnic, nationality, address, phone, gender, age)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (name.strip(), cnic.strip(), nationality.strip(), address.strip(), phone.strip(), gender, int(age)))
                st.success(f"Registered new patient: {name} (CNIC: {cnic}).")
            conn.commit()
            conn.close()

    st.markdown("---")
    st.subheader("Registered Patients")

    conn = get_connection()
    try:
        df = pd.read_sql("""
            SELECT patient_id, patient_name, cnic, nationality, phone, gender, age, address 
            FROM patients ORDER BY patient_id DESC
        """, conn)
        if df.empty:
            st.info("No registered patients yet.")
        else:
            st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Error loading patients: {e}")
    finally:
        conn.close()
