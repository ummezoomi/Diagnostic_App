import streamlit as st
import mysql.connector
import pandas as pd
import os
import random
import re

# ------------------- Input Validation Helper -------------------
def validate_patient_inputs(name, cnic, nationality, address, phone, gender, age):
    """
    Validate inputs. 
    Allows empty CNIC (auto-generates a placeholder).
    """
    # --- Basic cleanup ---
    name = name.strip().title()
    cnic = cnic.strip().replace("-", "").replace(" ", "")
    nationality = nationality.strip().title()
    address = address.strip()
    phone = phone.strip()
    gender = gender.strip()

    # --- Name Validation ---
    if not name or not re.match(r"^[A-Za-z\s]+$", name):
        return False, "Patient name must contain only letters and spaces."

    # --- CNIC Logic (Camp Friendly) ---
    # If CNIC is empty or just "0", we generate a unique dummy ID
    if not cnic or cnic == "0":
        # Generate a random 6 digit number for internal tracking
        rand_id = random.randint(100000, 999999)
        formatted_cnic = f"NO-ID-{rand_id}"
    else:
        # If they typed something, verify it contains only digits
        if not cnic.isdigit():
            return False, "CNIC must contain digits only."

        # Optional: You can remove the length check if you want to allow 
        # incomplete CNICs, but standard is 13.
        if len(cnic) != 13:
            return False, "CNIC must be 13 digits (or leave empty for patients without ID)."

        # Auto-format
        formatted_cnic = f"{cnic[:5]}-{cnic[5:12]}-{cnic[12:]}"

    # --- Other Validations ---
    if gender not in ["Male", "Female", "Other"]:
        return False, "Please select a valid gender."

    if not isinstance(age, int) or age < 0 or age > 120:
        return False, "Age must be a valid integer."

    return True, formatted_cnic

# Database Configuration
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
        return mysql.connector.connect(**db_config)
    except Exception as e:
        st.error(f"MySQL connection failed: {e}")
        st.stop()

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # REMOVED "UNIQUE" constraint from cnic definition for future setup
    c.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        patient_id INT AUTO_INCREMENT PRIMARY KEY,
        patient_name VARCHAR(255),
        cnic VARCHAR(20), 
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
    init_db()

    if not st.session_state.get("logged_in", False):
        st.warning("Please login to access this page.")
        st.stop()

    role = st.session_state.get("role", "")
    if role not in ["registration", "admin"]:
        st.error("You do not have permission to access patient registration.")
        st.stop()

    st.set_page_config(layout="centered", page_title="Patient Registration")
    st.title("🧾 Patient Registration")

    # --- Input Form ---
    with st.form("reg_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Patient Name")
            nationality = st.text_input("Nationality", value="Pakistani")
            phone = st.text_input("Phone Number")
            age = st.number_input("Age", min_value=0, max_value=120, step=1, value=0)

        with col2:
            # Added help text for the camp scenario
            cnic = st.text_input("CNIC (Leave empty if no ID)")
            gender = st.selectbox("Gender", ["", "Male", "Female", "Other"])
            address = st.text_area("Address")

        submitted = st.form_submit_button("Register Patient")

    if submitted:
        if not name.strip():
            st.warning("Patient Name is required.")
        else:
            # Validate
            is_valid, result = validate_patient_inputs(
                name, cnic, nationality, address, phone, gender, int(age)
            )

            if not is_valid:
                st.error(f"❌ Validation failed: {result}")
            else:
                final_cnic = result

                # --- SAVE LOGIC (ALWAYS INSERT) ---
                conn = get_connection()
                c = conn.cursor()
                try:
                    # We removed the Check/Update logic. We ONLY Insert now.
                    # This allows duplicates or default CNICs.
                    c.execute("""
                        INSERT INTO patients (patient_name, cnic, nationality, address, phone, gender, age)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (name.strip(), final_cnic, nationality.strip(), address.strip(), phone.strip(), gender, int(age)))

                    conn.commit()
                    new_id = c.lastrowid
                    st.success(f"✅ Registered: {name} (ID: {new_id}) - CNIC: {final_cnic}")

                except mysql.connector.Error as err:
                    # If you forgot to run the SQL command in Step 1, this error will pop up
                    if err.errno == 1062: # Duplicate entry error code
                        st.error("⚠️ Database Error: The 'CNIC' column is still set to UNIQUE in MySQL.")
                        st.code("ALTER TABLE patients DROP INDEX cnic;")
                        st.info("Run the code above in MySQL Workbench to fix this.")
                    else:
                        st.error(f"Database Error: {err}")
                finally:
                    conn.close()

    st.markdown("---")
    st.subheader("Registered Patients (Latest 10)")

    conn = get_connection()
    try:
        df = pd.read_sql("""
            SELECT patient_id, patient_name, cnic, gender, age, phone 
            FROM patients ORDER BY patient_id DESC LIMIT 10
        """, conn)
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Error loading patients: {e}")
    finally:
        conn.close()