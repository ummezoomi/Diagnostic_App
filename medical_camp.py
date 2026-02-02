import pandas as pd
import streamlit as st
import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
import os
import re

# --------- Config & Database Setup ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = "New_drug_list.csv"

# DATABASE CREDENTIALS - Update if needed
db_config = {
    "host": "127.0.0.1",
    "user": "root",
    "port": 3306,
    "password": "umerEMR123@",  # Your Password
    "database": "emr_system",   # Ensure this matches your DB name
    "connection_timeout": 10,
}

# --- Session State Init ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None
if "username" not in st.session_state:
    st.session_state["username"] = ""

# --- Database Connection Management ---

def get_connection():
    try:
        # Just create a fresh connection. It's fast and reliable.
        return mysql.connector.connect(**db_config)
    except Exception as e:
        st.error(f"MySQL connection failed: {e}")
        st.stop()

# --------- NEW: Load ICD Data from MySQL (Not CSV) ----------

@st.cache_data(ttl=None)
def load_icd_diagnosis_from_db():
    conn = get_connection()
    try:
        # Try lowercase first (standard)
        try:
            df = pd.read_sql("SELECT * FROM icd_diagnosis", conn)
        except:
            # If that fails, try uppercase (common in some MySQL imports)
            df = pd.read_sql("SELECT * FROM ICD_DIAGNOSIS", conn)

        # Safety: If SQL returns empty, return empty DF immediately
        if df.empty:
            st.warning("⚠️ Connected to DB, but 'icd_diagnosis' table is empty.")
            return pd.DataFrame(columns=["Diagnosis"])

        # --- Column Mapping Logic (Improved) ---
        possible_names = ["Diagnosis", "diagnosis", "Description", "description",
                          "Disease", "disease", "Name", "LONG_DESCRIPTION", "short_description"]

        found_col = None
        for name in possible_names:
            if name in df.columns:
                found_col = name
                break

        if found_col:
            df.rename(columns={found_col: "Diagnosis"}, inplace=True)
        else:
            # Fallback: Use the 2nd column (usually the name) or 1st if only 1 exists
            if len(df.columns) > 1:
                df.rename(columns={df.columns[1]: "Diagnosis"}, inplace=True)
            elif len(df.columns) == 1:
                df.rename(columns={df.columns[0]: "Diagnosis"}, inplace=True)

        return df
    except Exception as e:
        # Show the actual error so you can see it on the client screen
        st.error(f"Error loading ICD Diagnosis: {e}")
        return pd.DataFrame(columns=["Diagnosis"])
    finally:
        conn.close()

@st.cache_data(ttl=None)
def load_icd_symptoms_from_db():
    conn = get_connection()
    try:
        # Try exact name from your SQL file first, then fallback
        try:
            df = pd.read_sql("SELECT * FROM icd10_symptom_list_all", conn)
        except:
            df = pd.read_sql("SELECT * FROM ICD10_Symptom_List_All", conn)

        if df.empty:
            st.warning("⚠️ Connected to DB, but Symptom table is empty.")
            return pd.DataFrame(columns=["Symptom"])

        # --- Column Mapping Logic ---
        possible_names = ["Symptom", "symptom", "Description", "description", "symptom_text"]

        found_col = None
        for name in possible_names:
            if name in df.columns:
                found_col = name
                break

        if found_col:
            df.rename(columns={found_col: "Symptom"}, inplace=True)
        else:
            if len(df.columns) > 0:
                df.rename(columns={df.columns[0]: "Symptom"}, inplace=True)

        return df
    except Exception as e:
        st.error(f"Error loading Symptoms: {e}")
        return pd.DataFrame(columns=["Symptom"])
    finally:
        conn.close()

# --------- Stock helpers ----------
def load_stock(force_reload=False):
    conn = get_connection()
    # Just read what is in the database
    try:
        df = pd.read_sql("SELECT * FROM stock", conn)
        conn.close()

        # If the DB is actually empty, warn the user but don't crash
        if df.empty:
            st.warning("⚠️ The Stock table in MySQL is empty! Please import data manually via Workbench.")

        return df
    except Exception as e:
        st.error(f"Database Error: {e}")
        conn.close()
        return pd.DataFrame()

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # registration
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
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS visits (
        visit_id INT AUTO_INCREMENT PRIMARY KEY,
        patient_id INT,
        doctor_type VARCHAR(100),
        visit_date DATETIME,
        history TEXT,
        bp VARCHAR(20),
        heart_rate INT,
        sat_o2 FLOAT,
        temp FLOAT,
        rr INT,
        blood_glucose FLOAT,
        gender VARCHAR(10),
        age INT,
        symptoms TEXT,
        indications TEXT,
        medicines TEXT,
        dispensed VARCHAR(10),
        dispensed_details TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS stock (
        `key` VARCHAR(255) PRIMARY KEY,
        generic VARCHAR(255),
        brand VARCHAR(255),
        dosage_form VARCHAR(255),
        dose VARCHAR(100),
        expiry DATE,
        unit VARCHAR(50),
        stock_qty INT
    )
    """)

    conn.commit()
    conn.close()

# initialize DB on import
init_db()


def save_stock(df):
    """
    Safely updates stock details without deleting the table.
    Uses 'ON DUPLICATE KEY UPDATE' to handle changes.
    """
    conn = get_connection()
    cur = conn.cursor()

    # This SQL query says: "Try to insert. If the KEY exists, just update the columns."
    sql = """
    INSERT INTO stock (`key`, generic, brand, dosage_form, dose, expiry, unit, stock_qty)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        stock_qty = VALUES(stock_qty),
        expiry = VALUES(expiry),
        generic = VALUES(generic),
        brand = VALUES(brand),
        dosage_form = VALUES(dosage_form),
        dose = VALUES(dose),
        unit = VALUES(unit)
    """

    # Prepare data for batch execution
    # Ensure columns are in the exact order of the SQL statement above
    data = df[["key", "generic", "brand", "dosage_form", "dose", "expiry", "unit", "stock_qty"]].values.tolist()

    try:
        cur.executemany(sql, data)
        conn.commit()
    except Exception as e:
        st.error(f"❌ Error saving stock: {e}")
    finally:
        conn.close()

def deduct_stock_atomic(key, qty):
    """
    Directly subtracts quantity from the database.
    Prevents race conditions (where two users overwrite each other).
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        # This performs the math INSIDE the database
        cur.execute("UPDATE stock SET stock_qty = stock_qty - %s WHERE `key`=%s", (qty, key))
        conn.commit()
    except Exception as e:
        st.error(f"❌ Error deducting stock: {e}")
    finally:
        conn.close()

def load_stock_df():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM stock", conn)
    conn.close()
    return df

def refresh_stock():
    conn = get_connection()
    latest_stock = pd.read_sql("SELECT * FROM stock", conn)
    conn.close()
    st.session_state["stock_df"] = latest_stock.copy()

# --------- Input Validation Helpers ----------
def validate_patient_inputs(name, cnic, nationality, phone, gender, age):
    if not name or not re.match(r"^[A-Za-z\s]+$", name):
        return False, "Patient name must contain only letters and spaces."
    if not cnic.isdigit():
        return False, "CNIC must contain digits only."
    if len(cnic) not in [13, 14, 15]:
        return False, "CNIC must be approx 13 digits."
    if nationality and not re.match(r"^[A-Za-z\s]+$", nationality):
        return False, "Nationality must contain only letters and spaces."
    if phone and not re.match(r"^[0-9+]+$", phone):
        return False, "Phone number must contain only digits."
    if gender not in ["Male", "Female", "Other"]:
        return False, "Please select a valid gender."
    if not isinstance(age, int) or age < 0 or age > 120:
        return False, "Age must be a valid integer."
    return True, ""

# --------- Main App ----------
def run_app():
    st.set_page_config(layout="centered", page_title="Medical Camp EMR & Pharmacy")

    auth = st.session_state.get("logged_in", False) or st.session_state.get("authenticated", False)
    role = st.session_state.get("role", None)
    username = st.session_state.get("username", None)

    if not auth:
        st.warning("You are not authenticated. Please go to the login page.")
        st.stop()

    st.sidebar.markdown(f"**User:** {username}")
    st.sidebar.markdown(f"**Role:** {role}")

    if st.sidebar.button("Logout", key=f"sidebar_logout_{username}"):
        for key in ["logged_in", "authenticated", "role", "username"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    if "icd_df" not in st.session_state:
        with st.spinner("Loading Diagnosis Database..."):
            st.session_state["icd_df"] = load_icd_diagnosis_from_db()

    if "icd_symptoms_df" not in st.session_state:
        with st.spinner("Loading Symptoms Database..."):
            st.session_state["icd_symptoms_df"] = load_icd_symptoms_from_db()

    # Automatically load CSV into DB if "stock_df" isn't in session yet
    if "stock_loaded" not in st.session_state:
        load_stock()
        st.session_state["stock_loaded"] = True

    if "stock_df" not in st.session_state:
        st.session_state["stock_df"] = load_stock_df()
        # ----------------------------------------
    st.title("Medical Camp EMR System")

    # Check Database Status for ICD
    icd_count = len(st.session_state.get("icd_df", []))
    if icd_count == 0:
        st.warning("⚠️ Database Warning: ICD Diagnosis table is empty in MySQL.")

    # Determine visible tabs
    tabs = []
    if role == "admin":
        tabs = ["Patient Entry", "Patient Records", "Pharmacy Dispensation"]
    elif role == "doctor":
        tabs = ["Patient Entry", "Patient Records"]
    elif role == "pharmacy":
        tabs = ["Pharmacy Dispensation", "Patient Records"]
    elif role == "registration":
        tabs = ["Patient Entry"]
    else:
        st.error("Unknown role. Contact admin.")
        st.stop()

    tab_objs = st.tabs(tabs)

    # ---------- PATIENT ENTRY TAB ----------

    # Admin Zone
    if role == "admin":
        st.write("---")
        with st.expander("⚠️ Admin Database Controls"):
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🚨 RELOAD STOCK CSV"):
                    new_df = load_stock(force_reload=True)
                    st.session_state["stock_df"] = new_df
                    st.rerun()
            with col2:
                st.info("Re-reads 'New_drug_list.csv' and wipes current DB stock.")

    if "Patient Entry" in tabs:
        with tab_objs[tabs.index("Patient Entry")]:
            st.header("Patient Visit Entry")

            if role == "doctor":
                if st.button("🔄 Refresh Patient List"):
                    st.rerun()

            conn = get_connection()
            patients_df = pd.read_sql("SELECT patient_id, patient_name, cnic FROM patients ORDER BY patient_id DESC", conn)
            conn.close()

            patient_options = []
            if role in ["admin", "registration"]:
                patient_options.append("+ Register New Patient")

            for _, r in patients_df.iterrows():
                label = f"{int(r['patient_id'])} - {r['patient_name']} ({r['cnic']})"
                patient_options.append(label)

            if not patient_options:
                st.info("No patients available.")
                st.stop()

            selected_patient_label = st.selectbox("Select Registered Patient", options=patient_options, index=0)
            registering_new = (selected_patient_label == "+ Register New Patient")

            if registering_new and role not in ["admin", "registration"]:
                st.error("Permission denied: You cannot register new patients.")
                st.stop()

            # Personal Details
            st.subheader("Personal Details")
            if registering_new:
                p_name = st.text_input("Patient Name", key="reg_p_name")
                p_cnic = st.text_input("CNIC", key="reg_p_cnic")
                p_nationality = st.text_input("Nationality", key="reg_p_nationality")
                p_address = st.text_area("Address", key="reg_p_address")
                p_phone = st.text_input("Phone Number", key="reg_p_phone")
                p_gender = st.selectbox("Select Gender", ["", "Male", "Female", "Other"], key="reg_p_gender")
                p_age = st.number_input("Age", min_value=0, max_value=120, step=1, key="reg_p_age")
            else:
                pid = int(selected_patient_label.split(" - ")[0])
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT * FROM patients WHERE patient_id=%s", (pid,))
                row = cur.fetchone()
                conn.close()

                # Pre-fill read-only
                if row:
                    st.text_input("Patient Name", value=row[1], disabled=True)
                    st.text_input("CNIC", value=row[2], disabled=True)
                    p_name, p_cnic = row[1], row[2]
                    p_nationality, p_address, p_phone = row[3], row[4], row[5]
                    p_gender, p_age = row[6], row[7]

                    st.text_input("Age", value=str(p_age), disabled=True)
                else:
                    st.error("Patient not found in DB.")
                    st.stop()

            # Doctor Info
            st.subheader("Clinical Data")
            doctor_type = st.selectbox("Doctor Type", ["General Physician", "Cardiologist", "Pediatrician", "Dermatologist", "Other"], key="doctor_type")

            # Vitals
            st.subheader("Vitals")
            c1, c2, c3, c4 = st.columns(4)
            bp_sys = c1.number_input("BP Sys", 0)
            bp_dia = c2.number_input("BP Dia", 0)
            heart_rate = c3.number_input("HR (BPM)", 0)
            temp = c4.number_input("Temp (C)", 36.0)

            c5, c6, c7 = st.columns(3)
            sat_o2 = c5.number_input("O2 Sat %", 0, 100, 98)
            rr = c6.number_input("Resp Rate", 0)
            blood_glucose = c7.number_input("Glucose (mg/dL)", 0)

            patient_history = st.text_area("Patient History / Complaints")

            # --- SQL BASED SYMPTOMS (Updated with +/- options) ---
            st.subheader("Symptoms")
            symptom_df = st.session_state.get("icd_symptoms_df")
            symptom_list = symptom_df["Symptom"].dropna().unique().tolist() if symptom_df is not None else []

            # 1. Select Number of Rows
            num_symptoms = st.number_input("Number of Symptoms", min_value=1, max_value=10, value=1, key="num_sym_input")
            symptoms_selected = []

            # 2. Loop to create dropdowns
            for i in range(int(num_symptoms)):
                col1, col2 = st.columns([3, 1]) # Optional: Add a column for notes later if you want
                with col1:
                    # We add [""] so the box starts empty and looks cleaner
                    sym = st.selectbox(f"Symptom {i+1}", options=[""] + symptom_list, key=f"sym_select_{i}")
                    if sym:
                        symptoms_selected.append(sym)

            # --- SQL BASED DIAGNOSIS (Updated with +/- options) ---
            st.subheader("Diagnosis (ICD-10)")
            icd_df = st.session_state.get("icd_df")
            diag_list = icd_df["Diagnosis"].dropna().unique().tolist() if icd_df is not None else []

            # 1. Select Number of Rows
            num_diag = st.number_input("Number of Indications", min_value=1, max_value=10, value=1, key="num_diag_input")
            indications_selected = []

            # 2. Loop to create dropdowns
            for i in range(int(num_diag)):
                diag = st.selectbox(f"Indication {i+1}", options=[""] + diag_list, key=f"diag_select_{i}")
                if diag:
                    indications_selected.append(diag)

            # Medicine Entry
            st.subheader("Prescription")
            medicines = []
            stock_df = st.session_state.get("stock_df", pd.DataFrame())

            # Allow adding medicines dynamically
            num_meds = st.number_input("Number of Medicines", 1, 10, 1)

            for i in range(int(num_meds)):
                st.markdown(f"**Medicine {i+1}**")
                med_options = stock_df["generic"].dropna().unique().tolist() if not stock_df.empty else []
                sel_generic = st.selectbox(f"Medicine {i+1}", [""] + med_options, key=f"med_{i}")

                if sel_generic:
                    row = stock_df[stock_df["generic"] == sel_generic].iloc[0]
                    c1, c2, c3 = st.columns(3)
                    freq = c1.text_input(f"Freq {i+1}", "1+0+1")
                    time_day = c2.text_input(f"Time {i+1}", "After Meal")
                    amount = c3.text_input(f"Days/Qty {i+1}", "3 Days")

                    medicines.append({
                        "generic": row["generic"],
                        "brand": row["brand"],
                        "frequency": freq,
                        "time": time_day,
                        "amount": amount
                    })

            if st.button("Save Visit"):
                if registering_new:
                    valid, msg = validate_patient_inputs(p_name, p_cnic, p_nationality, p_phone, p_gender, int(p_age))
                    if not valid:
                        st.error(msg)
                        st.stop()

                conn = get_connection()
                cur = conn.cursor()

                # 1. Handle Patient
                if registering_new:
                    # check exist
                    cur.execute("SELECT patient_id FROM patients WHERE cnic=%s", (p_cnic,))
                    exist = cur.fetchone()
                    if exist:
                        patient_id = exist[0]
                        # Update details
                        cur.execute("UPDATE patients SET patient_name=%s, age=%s WHERE patient_id=%s", (p_name, p_age, patient_id))
                    else:
                        cur.execute("INSERT INTO patients (patient_name, cnic, nationality, address, phone, gender, age) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                                    (p_name, p_cnic, p_nationality, p_address, p_phone, p_gender, p_age))
                        patient_id = cur.lastrowid
                else:
                    patient_id = pid

                # 2. Insert Visit
                med_str = "; ".join([f"{m['generic']} [{m['brand']}] ({m['frequency']}, {m['amount']})" for m in medicines])

                cur.execute("""
                    INSERT INTO visits (patient_id, doctor_type, visit_date, history, bp, heart_rate, sat_o2, temp, blood_glucose, gender, age, symptoms, indications, medicines, dispensed)
                    VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'No')
                """, (patient_id, doctor_type, patient_history, f"{bp_sys}/{bp_dia}", heart_rate, sat_o2, temp, blood_glucose, p_gender, p_age,
                      "; ".join(symptoms_selected), "; ".join(indications_selected), med_str))

                conn.commit()
                conn.close()
                st.success("Visit Saved Successfully!")

    # ---------- PATIENT RECORDS TAB (The "Good" Version) ----------
    if "Patient Records" in tabs:
        with tab_objs[tabs.index("Patient Records")]:
            st.header("All Patient Records")

            # 1. Refresh Button
            if st.button("🔄 Refresh Records"):
                st.rerun()

            # 2. Fetch Combined Data (Patients + Visits)
            conn = get_connection()
            try:
                df = pd.read_sql("""
                    SELECT 
                        p.patient_id,
                        p.patient_name,
                        p.cnic,
                        v.visit_id,
                        v.doctor_type,
                        v.visit_date,
                        v.history,
                        v.bp,
                        v.heart_rate,
                        v.symptoms,
                        v.indications,
                        v.medicines,
                        v.dispensed,
                        v.dispensed_details
                    FROM patients p
                    LEFT JOIN visits v ON p.patient_id = v.patient_id
                    ORDER BY v.visit_date DESC, p.patient_id DESC
                """, conn)
            except Exception as e:
                st.error(f"Error fetching records: {e}")
                df = pd.DataFrame()
            finally:
                conn.close()

            # 3. Display the Big Table
            if df.empty:
                st.info("No patients or visits recorded yet.")
            else:
                st.dataframe(df, use_container_width=True)

            # 4. Management / Deletion Tools
            if role in ["admin", "doctor"]:
                st.write("---")
                st.subheader("Manage Records")

                c1, c2 = st.columns(2)

                # ----- Column 1: Delete Single Visit -----
                with c1:
                    st.markdown("##### 🗑️ Delete Specific Visit")
                    if "visit_id" in df.columns and df["visit_id"].notna().any():
                        # Filter out None/NaN visit IDs (from patients with no visits)
                        valid_visits = df["visit_id"].dropna().unique().astype(int).astype(str).tolist()

                        del_visit = st.selectbox(
                            "Select Visit ID",
                            options=[""] + valid_visits,
                            key="delete_visit_select"
                        )

                        if st.button("Confirm Delete Visit", type="primary"):
                            if del_visit:
                                conn = get_connection()
                                cur = conn.cursor()
                                cur.execute("DELETE FROM visits WHERE visit_id=%s", (int(del_visit),))
                                conn.commit()
                                conn.close()
                                st.success(f"✅ Visit ID {del_visit} deleted.")
                                st.rerun()
                            else:
                                st.warning("Select a Visit ID first.")
                    else:
                        st.info("No visits to delete.")

                # ----- Column 2: Delete Entire Patient -----
                with c2:
                    st.markdown("##### 🧹 Delete Patient (and all their visits)")
                    if "patient_id" in df.columns:
                        all_patients = df["patient_id"].unique().astype(str).tolist()

                        del_patient = st.selectbox(
                            "Select Patient ID",
                            options=[""] + all_patients,
                            key="delete_patient_select"
                        )

                        if st.button("Confirm Delete Patient", type="primary"):
                            if del_patient:
                                conn = get_connection()
                                cur = conn.cursor()
                                # 1. Delete visits first (Foreign Key constraint)
                                cur.execute("DELETE FROM visits WHERE patient_id=%s", (int(del_patient),))
                                # 2. Delete patient
                                cur.execute("DELETE FROM patients WHERE patient_id=%s", (int(del_patient),))
                                conn.commit()
                                conn.close()
                                st.success(f"✅ Patient ID {del_patient} wiped from database.")
                                st.rerun()
                            else:
                                st.warning("Select a Patient ID first.")

            conn.close()
    # ---------- PHARMACY DISPENSATION TAB (RESTORED) ----------
    if "Pharmacy Dispensation" in tabs:
        with tab_objs[tabs.index("Pharmacy Dispensation")]:
            st.header("Pharmacy Dispensation")

            # 1. Refresh Stock Button
            if st.button("🔄 Refresh Stock from DB"):
                refresh_stock()
                st.success("Stock refreshed.")

            # Ensure stock is loaded
            if "stock_df" not in st.session_state:
                st.session_state["stock_df"] = load_stock_df()
            stock_df = st.session_state["stock_df"]

            # 2. Select Patient
            conn = get_connection()
            patients_df = pd.read_sql("SELECT * FROM patients", conn)

            if patients_df.empty:
                conn.close()
                st.info("No patient records found. Go to 'Patient Entry' to register someone.")
            else:
                # Create a list like "101 - John Doe"
                patient_ids = patients_df["patient_id"].tolist()
                patient_labels = [f"{row['patient_id']} - {row['patient_name']}" for _, row in patients_df.iterrows()]

                selected_patient_label = st.selectbox("Select Patient to Dispense For", options=[""] + patient_labels, index=0)

                if selected_patient_label:
                    # Extract ID from string "101 - John Doe"
                    selected_patient_id = int(selected_patient_label.split(" - ")[0])

                    # 3. Load Visits for this Patient
                    visits_df = pd.read_sql(
                        "SELECT visit_id, visit_date, doctor_type, medicines, dispensed FROM visits WHERE patient_id=%s ORDER BY visit_date DESC",
                        conn, params=(selected_patient_id,)
                    )
                    conn.close() # Close early to free resource

                    if visits_df.empty:
                        st.info("No visits found for this patient.")
                    else:
                        # 4. Filter Mode (Pending vs All)
                        filter_mode = st.radio("Show visits:", ["Pending (not dispensed)", "All", "Dispensed"], index=0, horizontal=True)

                        if filter_mode == "Pending (not dispensed)":
                            view_df = visits_df[visits_df["dispensed"].fillna("No") != "Yes"]
                        elif filter_mode == "Dispensed":
                            view_df = visits_df[visits_df["dispensed"].fillna("No") == "Yes"]
                        else:
                            view_df = visits_df

                        # 5. Select Specific Visit
                        visit_options = [f"{int(r.visit_id)} — {r.visit_date} ({r.doctor_type})" for r in view_df.itertuples()] if not view_df.empty else []

                        if not visit_options:
                            st.warning("No visits match this filter.")
                        else:
                            selected_visit_label = st.selectbox("Select Visit", options=[""] + visit_options, index=0)

                            if selected_visit_label:
                                visit_id = int(selected_visit_label.split(" — ")[0])
                                visit_row = view_df[view_df["visit_id"] == visit_id].iloc[0]

                                # 6. Parse Medicines (YOUR LOGIC)
                                raw_meds = str(visit_row.get("medicines", "")).split(";")
                                st.subheader(f"Dispensing for Visit ID: {visit_id}")
                                st.write(f"**Doctor:** {visit_row['doctor_type']}")

                                dispense_plan = []

                                # Grid Header
                                c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 2])
                                c1.markdown("**Medicine**")
                                c2.markdown("**Brand**")
                                c3.markdown("**Stock**")
                                c4.markdown("**Prescribed**")
                                c5.markdown("**Dispense Qty**")
                                st.divider()

                                for i, raw in enumerate(raw_meds):
                                    med_text = raw.strip()
                                    if med_text == "": continue

                                    # Regex parsing
                                    brand_match = re.search(r"\[([^\]]+)\]", med_text)
                                    brand = brand_match.group(1).strip() if brand_match else ""
                                    generic = med_text.split("[")[0].strip()
                                    generic_norm = generic.lower()

                                    # Find matching stock
                                    possible_brands = stock_df[stock_df["generic"].str.lower() == generic_norm]
                                    brand_options = possible_brands["brand"].unique().tolist()

                                    # Auto-select brand if only one exists, or let user pick
                                    selected_brand = brand # Default to prescribed brand
                                    if not possible_brands.empty:
                                        # If the prescribed brand isn't in stock, or multiple options exist
                                        if len(brand_options) > 0:
                                            # Try to find the prescribed brand in the options
                                            default_ix = 0
                                            if brand in brand_options:
                                                default_ix = brand_options.index(brand)

                                            selected_brand = st.selectbox(
                                                f"Brand for {generic}",
                                                options=brand_options,
                                                index=default_ix,
                                                key=f"br_{visit_id}_{i}",
                                                label_visibility="collapsed"
                                            )

                                    # Get precise stock row
                                    matched = stock_df[
                                        (stock_df["generic"].str.strip().str.lower() == generic_norm) &
                                        (stock_df["brand"].str.strip().str.lower() == selected_brand.lower())
                                        ]

                                    stock_qty = int(matched.iloc[0]["stock_qty"]) if not matched.empty else 0

                                    # Parse amount (e.g., "3 Days")
                                    prescribed_match = re.search(r"\(([^)]*)\)", med_text)
                                    prescribed_details = prescribed_match.group(1) if prescribed_match else ""

                                    # Render Row
                                    c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 2])
                                    with c1: st.write(f"{generic}")
                                    with c2: st.write(f"{selected_brand}")
                                    with c3: st.write(f"{stock_qty}")
                                    with c4: st.caption(prescribed_details)
                                    with c5:
                                        qty_to_dispense = st.number_input(
                                            "Qty", min_value=0, max_value=stock_qty, value=0, step=1,
                                            key=f"qty_{visit_id}_{i}", label_visibility="collapsed"
                                        )

                                    dispense_plan.append({
                                        "display": f"{generic} [{selected_brand}]",
                                        "generic": generic,
                                        "brand": selected_brand,
                                        "dispense_qty": int(qty_to_dispense),
                                        "matched_index": matched.index[0] if not matched.empty else None
                                    })
                                    st.divider()

                                # 7. Confirm Button
                                if st.button("✅ Confirm Dispensation"):
                                    to_dispense = [d for d in dispense_plan if d["dispense_qty"] > 0]

                                    if not to_dispense:
                                        st.error("Please enter a quantity greater than 0 for at least one medicine.")
                                    else:
                                        dispensed_summary = []
                                        try:
                                            # --- NEW ATOMIC LOGIC ---
                                            for d in to_dispense:
                                                if d["matched_index"] is not None:
                                                    # 1. Get the Key directly from the dataframe
                                                    idx = d["matched_index"]
                                                    item_key = stock_df.at[idx, "key"]

                                                    # 2. Deduct safely from DB
                                                    deduct_stock_atomic(item_key, d["dispense_qty"])

                                                    # 3. Add to summary log
                                                    dispensed_summary.append(f"{d['display']} (Qty: {d['dispense_qty']})")
                                                else:
                                                    st.error(f"Error finding key for {d['display']}")

                                            # 4. Update Visit Record
                                            summary_str = "; ".join(dispensed_summary)
                                            conn2 = get_connection()
                                            cur2 = conn2.cursor()
                                            cur2.execute(
                                                "UPDATE visits SET dispensed='Yes', dispensed_details=%s WHERE visit_id=%s",
                                                (summary_str, visit_id)
                                            )
                                            conn2.commit()
                                            conn2.close()

                                            # 5. Refresh Data from DB (So UI shows new true values)
                                            refresh_stock()
                                            st.success("Dispensation Saved! Inventory Updated.")
                                            st.rerun()

                                        except Exception as e:
                                            st.error(f"Error saving dispensation: {e}")
if __name__ == "__main__":
    run_app()