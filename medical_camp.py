# main_app.py
import pandas as pd
import streamlit as st
import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
import os
import re
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None
if "username" not in st.session_state:
    st.session_state["username"] = ""

# --------- Config ----------
EXCEL_FILE = "New_drug_list.csv"
def load_icd_diagnosis():
    try:
        # Change this based on your file format
        df = pd.read_csv("icd_diagnosis.csv")   # or pd.read_excel("icd_diagnosis.xlsx")
        if "Diagnosis" in df.columns:
            return df
        else:
            st.warning("ICD file found but 'Diagnosis' column missing.")
            return pd.DataFrame(columns=["Diagnosis"])
    except Exception as e:
        st.error(f"Error loading ICD diagnosis file: {e}")
        return pd.DataFrame(columns=["Diagnosis"])

# Load once at start
if "icd_df" not in st.session_state:
    st.session_state["icd_df"] = load_icd_diagnosis()


# Initialize a pool (do this globally, outside the function)
db_config = {
    "host": "127.0.0.1",
    "user": "root",
    "port": 3306,
    "password": "umerEMR123@",
    "database": "emr_system",
    "connection_timeout": 5,
    "auth_plugin" : "mysql_native_password"
}

@st.cache_resource
def get_db_pool():
    # This creates a pool of connections that stays open
    return MySQLConnectionPool(pool_name="emr_pool", pool_size=20, **db_config)

def get_connection():
    try:
        pool = get_db_pool()
        return pool.get_connection()
    except Exception as e:
        st.error(f"MySQL connection failed: {e}")
        st.stop()

def load_icd_symptoms():
    try:
        df = pd.read_csv("ICD10_Symptom_List_All.csv")
        if "Symptom" in df.columns and "Body_System" in df.columns:
            return df
        else:
            st.warning("Symptom file missing 'Symptom' or 'Body_System' column.")
            return pd.DataFrame(columns=["Symptom", "Body_System"])
    except Exception as e:
        st.error(f"Error loading ICD symptoms file: {e}")
        return pd.DataFrame(columns=["Symptom", "Body_System"])

# Load once at start
if "icd_symptoms_df" not in st.session_state:
    st.session_state["icd_symptoms_df"] = load_icd_symptoms()

# --------- Stock helpers ----------
def load_stock(force_reload=False):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    # Absolute path setup
    stock_file_path = os.path.join(BASE_DIR, EXCEL_FILE)

    # Check if table has data
    cur.execute("SELECT count(*) as cnt FROM stock")
    result = cur.fetchone()
    count = result['cnt']

    # LOGIC: Load if table is empty OR if force_reload is True
    if count == 0 or force_reload:
        if os.path.exists(stock_file_path):
            try:
                # 1. If forcing, wipe the table first
                if force_reload:
                    cur.execute("TRUNCATE TABLE stock")
                    st.warning("⚠️ Old stock data wiped.")

                # 2. Load CSV
                stock = pd.read_csv(stock_file_path)

                # ... (Your existing data cleaning logic) ...
                stock.columns = stock.columns.str.strip()
                stock["StockQty"] = stock.get("Quantity", 0).fillna(0).astype(int)
                stock["Generic"] = stock["Generic"].fillna("").str.strip().str.title()
                stock["Brand"] = stock["Brand"].fillna("").str.strip().str.title()
                stock["Dosage Form"] = stock["Dosage Form"].fillna("").str.strip().str.title()
                stock["Dose"] = stock["Dose"].fillna("").str.strip()
                stock["Expiry"] = pd.to_datetime(stock["Expiry"], errors="coerce").dt.date
                stock["Unit"] = stock.get("Unit","").fillna("").str.strip().str.lower()
                stock = stock[(stock["Generic"]!="") | (stock["Brand"]!="")].copy()
                stock["Key"] = stock["Generic"].str.lower() + "||" + stock["Brand"].str.lower()

                # 3. Insert
                cur.executemany("""
                    INSERT INTO stock (`key`, generic, brand, dosage_form, dose, expiry, unit, stock_qty)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, stock[["Key","Generic","Brand","Dosage Form","Dose","Expiry","Unit","StockQty"]].values.tolist())

                conn.commit()
                st.success(f"✅ Successfully imported {len(stock)} medicines from CSV!")

            except Exception as e:
                st.error(f"❌ Error importing CSV: {e}")
        else:
            st.error(f"❌ CSV File not found at: {stock_file_path}")
    else:
        # Debug message (so you know why it skipped)
        print(f"Skipped CSV import: Database already has {count} records.")

    # Always return the fresh dataframe
    cur.execute("SELECT * FROM stock")
    rows = cur.fetchall()
    conn.close()
    return pd.DataFrame(rows)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # registration (personal info only)
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
# Automatically load CSV into DB if "stock_df" isn't in session yet
if "stock_loaded" not in st.session_state:
    load_stock()
    st.session_state["stock_loaded"] = True


def save_stock(df):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM stock")
    for _, row in df.iterrows():
        cur.execute("""
            INSERT INTO stock (`key`, generic, brand, dosage_form, dose, expiry, unit, stock_qty)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, tuple(row))
    conn.commit()

# session stock init helper
#@st.cache_data
def load_stock_df():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM stock", conn)
    conn.close()
    return df

if "stock_df" not in st.session_state:
    st.session_state["stock_df"] = load_stock_df()


def refresh_stock():
    conn = get_connection()
    latest_stock = pd.read_sql("SELECT * FROM stock", conn)
    conn.close()
    st.session_state["stock_df"] = latest_stock.copy()
# --------- Input Validation Helpers ----------
def validate_patient_inputs(name, cnic, nationality, phone, gender, age):
    """
    Validate patient registration inputs.
    Returns (True, "") if all valid, else (False, "error message").
    """
    # Validate name: should be alphabetic (with spaces allowed)
    if not name or not re.match(r"^[A-Za-z\s]+$", name):
        return False, "Patient name must contain only letters and spaces (no numbers or symbols)."

    # Validate CNIC: only digits, typically 13 or so
    if not cnic.isdigit():
        return False, "CNIC must contain digits only."
    if len(cnic) not in [13, 14, 15]:  # flexible, in case of minor format differences
        return False, "CNIC must be 13 digits (or close to that length)."

    # Nationality: letters only
    if nationality and not re.match(r"^[A-Za-z\s]+$", nationality):
        return False, "Nationality must contain only letters and spaces."

    # Phone number: digits + optional '+' sign
    if phone and not re.match(r"^[0-9+]+$", phone):
        return False, "Phone number must contain only digits (and '+' if international)."

    # Gender: ensure selected
    if gender not in ["Male", "Female", "Other"]:
        return False, "Please select a valid gender."

    # Age: numeric and reasonable range
    if not isinstance(age, int) or age < 0 or age > 120:
        return False, "Age must be a valid integer between 0 and 120."

    return True, ""

# --------- Main App ----------
def run_app():
    st.set_page_config(layout="centered", page_title="Medical Camp EMR & Pharmacy")

    # Unified login state (check either logged_in or authenticated)
    auth = st.session_state.get("logged_in", False) or st.session_state.get("authenticated", False)
    role = st.session_state.get("role", None)
    username = st.session_state.get("username", None)

    if not auth:
        st.warning("You are not authenticated. Please go to the login page.")
        st.stop()

    # Sidebar user info + logout
    st.sidebar.markdown(f"**User:** {username}")
    st.sidebar.markdown(f"**Role:** {role}")
    if st.sidebar.button("Logout", key=f"sidebar_logout_{st.session_state.get('username', '')}"):

        # clear session and go back to login
        for key in ["logged_in", "authenticated", "role", "username"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.title("Medical Camp EMR System")
    st.write("Enter patient details, symptoms, possible indications, and prescribed medicines.")

    # Determine visible tabs based on role
    tabs = []
    if role == "admin":
        tabs = ["Patient Entry", "Patient Records", "Pharmacy Dispensation"]
    elif role == "doctor":
        tabs = ["Patient Entry", "Patient Records"]
    elif role == "pharmacy":
        tabs = ["Pharmacy Dispensation", "Patient Records"]
    else:
        st.error("Unknown role. Contact admin.")
        st.stop()

    tab_objs = st.tabs(tabs)

    # ---------- Utility: get next patient id ----------
    def get_next_patient_id():
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT patient_id FROM patients ORDER BY patient_id DESC LIMIT 1")
            last = cur.fetchone()

            conn.close()
            if last and last[0]:
                try:
                    nid = str(int(last[0]) + 1)
                except Exception:
                    # if last id not integer, just return 1 or a timestamp
                    nid = str(int(pd.Timestamp.now().timestamp()))
            else:
                nid = "1"
            return nid
        except Exception:
            conn.close()
            return "1"

    # ---------- PATIENT ENTRY TAB ----------
    st.write("---")
    st.subheader("⚠️ Admin Zone")

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🚨 FORCE RELOAD STOCK"):
            # This calls the function with force_reload=True
            new_df = load_stock(force_reload=True)
            st.session_state["stock_df"] = new_df
            st.rerun()
    with col2:
        st.info("Click this ONLY if you updated 'Drug list.csv' and need to reset the database.")
    if "Patient Entry" in tabs:
        with tab_objs[tabs.index("Patient Entry")]:
            st.header("Patient Visit Entry")

            if role == "doctor":
                st.write("")  # small spacing
                if st.button("🔄 Refresh Patient List"):
                    st.rerun()

            conn = get_connection()
            patients_df = pd.read_sql("SELECT patient_id, patient_name, cnic FROM patients ORDER BY patient_id DESC", conn)
            conn.close()

            # Build selection: register new OR choose existing
            conn = get_connection()
            patients_df = pd.read_sql("SELECT patient_id, patient_name, cnic FROM patients ORDER BY patient_id DESC", conn)
            conn.close()

            patient_options = []

            # Only admin and registration users can register new patients
            if role in ["admin", "registration"]:
                patient_options.append("+ Register New Patient")

            # Add all existing patients
            for _, r in patients_df.iterrows():
                label = f"{int(r['patient_id'])} - {r['patient_name']} ({r['cnic']})"
                patient_options.append(label)

            if len(patient_options) == 0:
                st.info("No patients available. Please contact the registration desk to add new patients.")
                st.stop()

            selected_patient_label = st.selectbox("Select Registered Patient", options=patient_options, index=0)

            registering_new = (selected_patient_label == "+ Register New Patient")

            # Prevent doctors/pharmacy from adding new patients
            if registering_new and role not in ["admin", "registration"]:
                st.error("You do not have permission to register new patients.")
                st.stop()


    # Personal details (either register new - editable, OR display selected patient's info read-only)
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
                # parse patient_id from label
                pid = int(selected_patient_label.split(" - ")[0])
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT * FROM patients WHERE patient_id=%s", (pid,))
                row = cur.fetchone()
                conn.close()
                # row order: patient_id, patient_name, cnic, nationality, address, phone, gender, age
                if row:
                    st.text_input("Patient Name", value=row[1], disabled=True)
                    st.text_input("CNIC", value=row[2], disabled=True)
                    st.text_input("Nationality", value=row[3] or "", disabled=True)
                    st.text_area("Address", value=row[4] or "", disabled=True)
                    st.text_input("Phone Number", value=row[5] or "", disabled=True)
                    st.text_input("Gender", value=row[6] or "", disabled=True)
                    st.text_input("Age", value=str(row[7]) if row[7] is not None else "", disabled=True)
                # store for later
                p_name, p_cnic, p_nationality, p_address, p_phone, p_gender, p_age = row[1], row[2], row[3], row[4], row[5], row[6], row[7]
            # Doctor Information
            st.subheader("Doctor Information")
            doctor_type = st.selectbox(
                "Doctor Type",
                ["Dermatologist", "Gynecologist", "Cardiologist", "General Physician", "Pediatrician", "Other"],
                key="doctor_type"
            )
            doctor_name = st.text_input("Doctor Name", key="doctor_name")

            # Visit Notes / History
            st.subheader("Patient History / Notes")
            patient_history = st.text_area("Enter relevant patient history, observations, or complaints", key="patient_history")
            st.subheader("Vitals")
            col1, col2, col3 = st.columns(3)
            with col1:
                bp_sys = st.number_input("BP Systolic", min_value=0, step=1, key="bp_sys")
            with col2:
                bp_dia = st.number_input("BP Diastolic", min_value=0, step=1, key="bp_dia")
            with col3:
                heart_rate = st.number_input("Heart Rate (BPM)", min_value=0, step=1, key="heart_rate")

            col4, col5, col6, col7 = st.columns(4)
            with col4:
                sat_o2 = st.number_input("SatO2 (%)", min_value=0, max_value=100, step=1, key="sat_o2")
            with col5:
                temp = st.number_input("Temp (°C)", min_value=25.0, max_value=45.0, step=0.1, key="temp")
            with col6:
                rr = st.number_input("Respiration Rate (RR)", min_value=0, step=1, key="rr")
            with col7:
                blood_glucose = st.number_input("Blood Glucose (mg/dL)", min_value=0, step=1, key="blood_glucose")

            st.subheader("Symptoms (Up to 8)")
            symptoms = []
            symptom_df = st.session_state.get("icd_symptoms_df")
            symptom_options = symptom_df["Symptom"].dropna().unique().tolist() if symptom_df is not None else []
            for i in range(1, 9):
                selected_symptom = st.selectbox(
                    f"Select Symptom {i}",
                    options=[""] + symptom_options,
                    key=f"symptom_{i}"
                )
                if selected_symptom:
                    symptoms.append(selected_symptom)

            st.subheader("Possible Indications (Up to 4)")
            icd_df = st.session_state.get("icd_df")
            if icd_df is not None and not icd_df.empty and "Diagnosis" in icd_df.columns:
                diagnosis_options = icd_df["Diagnosis"].dropna().unique().tolist()
            else:
                diagnosis_options = []
                st.warning("ICD diagnosis list missing or empty.")

            indications = []
            for i in range(1, 5):
                selected_icd = st.selectbox(
                    f"Select ICD Diagnosis {i}",
                    options=[""] + diagnosis_options,
                    key=f"icd_diag_{i}"
                )
                if selected_icd:
                    indications.append(selected_icd)   # <-- fixed: append selected ICDs

            st.subheader("Medicines (Up to 10)")
            medicines = []
            # keep your medicines UI mostly same (uses stock_df)
            stock_df = st.session_state.get("stock_df", pd.DataFrame())
            for i in range(1, 11):
                st.markdown(f"**Medicine {i}**")
                med_options = stock_df["generic"].dropna().unique().tolist() if not stock_df.empty else []
                sel_generic = st.selectbox(f"Pick medicine [{i}]", [""] + med_options, key=f"med_sel_{i}")
                if sel_generic:
                    row = stock_df[stock_df["generic"] == sel_generic].iloc[0]
                    generic = row["generic"]
                    brand = row["brand"]
                    form = row["dosage_form"]
                    dose = row.get("dose","")
                    expiry = row.get("expiry","")
                    stockqty = row.get("stock_qty",0)
                    col1, col2, col3 = st.columns([1,1,1])
                    with col1:
                        freq = st.text_input(f"Frequency [{i}]", key=f"med_freq_{i}", label_visibility="collapsed", placeholder="Frequency")
                    with col2:
                        time_day = st.text_input(f"Time [{i}]", key=f"med_time_{i}", label_visibility="collapsed", placeholder="Time of Day")
                    with col3:
                        amount = st.text_input(f"Amount [{i}]", key=f"med_amount_{i}", label_visibility="collapsed", placeholder="Amount")
                    st.caption(f"Brand: {brand}, Form: {form}, Dose: {dose}, Expiry: {expiry}, Stock: {stockqty}")
                    medicines.append({
                        "generic": generic,
                        "brand": brand,
                        "form": form,
                        "dose": dose,
                        "expiry": expiry,
                        "stock_qty": stockqty,
                        "frequency": freq.strip(),
                        "time": time_day.strip(),
                        "amount": amount.strip()
                    })

            if st.button("Save Visit Record"):
                # validation: must have patient information and some content
                if registering_new:
                    is_valid, msg = validate_patient_inputs(p_name.strip(), p_cnic.strip(), p_nationality.strip(), p_phone.strip(), p_gender, int(p_age))
                    if not is_valid:
                        st.error("For new patients, Patient Name and CNIC are required.")
                        st.stop()
                # ensure patient exists or get patient_id
                conn = get_connection()
                cur = conn.cursor()
                if registering_new:
                    # insert or update (if CNIC exists, update)
                    cur.execute("SELECT patient_id FROM patients WHERE cnic=%s", (p_cnic.strip(),))
                    existing = cur.fetchone()
                    if existing:
                        patient_id = int(existing[0])
                        cur.execute("""
                            UPDATE patients SET patient_name=%s, nationality=%s, address=%s, phone=%s, gender=%s, age=%s
                            WHERE patient_id=%s
                        """, (p_name.strip(), p_nationality.strip(), p_address.strip(), p_phone.strip(), p_gender, int(p_age), patient_id))
                    else:
                        cur.execute("""
                            INSERT INTO patients (patient_name, cnic, nationality, address, phone, gender, age) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (p_name.strip(), p_cnic.strip(), p_nationality.strip(), p_address.strip(), p_phone.strip(), p_gender, int(p_age)))
                        patient_id = cur.lastrowid
                else:
                    patient_id = int(selected_patient_label.split(" - ")[0])

                # prepare visit record
                visit_record = (
                    patient_id,
                    doctor_type,  # from your existing selectbox variable, ensure you keep it in your larger code
                    str(pd.Timestamp.now()),
                    patient_history if 'patient_history' in locals() else "",  # if you have history variable
                    f"{bp_sys}/{bp_dia}",
                    int(heart_rate),
                    float(sat_o2),
                    float(temp),
                    int(rr),
                    float(blood_glucose),
                    p_gender,
                    int(p_age) if p_age is not None else None,
                    "; ".join(symptoms),
                    "; ".join(indications),
                    "; ".join([f"{m['generic']} [{m['brand']}] ({m['frequency']}, {m['time']}, {m['amount']})" for m in medicines]),
                    "No",
                    "",
                )
                cur.execute("""
                    INSERT INTO visits
                    (patient_id, doctor_type, visit_date, history, bp, heart_rate, sat_o2, temp, resp_rate, blood_glucose, gender, age, symptoms, indications, medicines, dispensed, dispensed_details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, visit_record)
                conn.commit()
                conn.close()
                st.success("Visit saved successfully (linked to patient).")
                # Optionally show what was saved:
                st.json({
                    "patient_id": patient_id,
                    "symptoms": "; ".join(symptoms),
                    "indications": "; ".join(indications),
                    "medicines": visit_record[13]
                })


# ---------- PATIENT RECORDS TAB ----------
    if "Patient Records" in tabs:
        with tab_objs[tabs.index("Patient Records")]:
            st.header("All Patient Records")

            conn = get_connection()
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
                ORDER BY p.patient_id DESC
            """, conn)
            conn.close()

            if df.empty:
                st.info("No patients or visits recorded yet.")
            else:
                st.dataframe(df, use_container_width=True)

            # --- Deletion Options ---
            if role in ["admin", "doctor"]:
                st.subheader("Manage Records")

                # ----- Option 1: Delete Visit -----
                if "visit_id" in df.columns and df["visit_id"].notna().any():
                    del_visit = st.selectbox(
                        "Select Visit ID to delete",
                        options=[""] + df["visit_id"].dropna().astype(str).tolist(),
                        index=0,
                        key="delete_visit"
                    )
                    if st.button("🗑️ Delete Visit"):
                        if del_visit:
                            conn = get_connection()
                            cur = conn.cursor()
                            cur.execute("DELETE FROM visits WHERE visit_id=%s", (int(del_visit),))
                            conn.commit()
                            conn.close()
                            st.success(f"✅ Visit ID {del_visit} deleted successfully.")
                            st.rerun()
                        else:
                            st.warning("Please select a valid Visit ID.")

                # ----- Option 2: Delete Patient -----
                del_patient = st.selectbox(
                    "Select Patient ID to delete",
                    options=[""] + df["patient_id"].dropna().astype(str).tolist(),
                    index=0,
                    key="delete_patient"
                )
                if st.button("🧹 Delete Patient Record"):
                    if del_patient:
                        conn = get_connection()
                        cur = conn.cursor()
                        # Delete any related visits first (to avoid foreign key conflicts)
                        cur.execute("DELETE FROM visits WHERE patient_id=%s", (int(del_patient),))
                        cur.execute("DELETE FROM patients WHERE patient_id=%s", (int(del_patient),))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Patient ID {del_patient} and their visits deleted successfully.")
                        st.rerun()
                    else:
                        st.warning("Please select a valid Patient ID.")


    # ---------- PHARMACY DISPENSATION TAB ----------
    if "Pharmacy Dispensation" in tabs:
        with tab_objs[tabs.index("Pharmacy Dispensation")]:
            st.header("Pharmacy Dispensation")
            if st.button("🔄 Refresh Stock"):
                refresh_stock()
                st.success("Stock refreshed from database.")
            stock_df = st.session_state["stock_df"]

            # Debug / basic stock table
            st.write("Stock (generic, brand, qty):")
            st.dataframe(stock_df[["generic", "brand", "stock_qty"]], use_container_width=True)

            # Stock management (quick edit)
            with st.expander("🔧 Stock Management (view / quick edit)"):
                st.write("Update stock quantities. Saved to database.")
                editable = stock_df.copy()
                for idx, row in editable.iterrows():
                    c1, c2, c3 = st.columns([4,1,1])
                    with c1:
                        st.write(f"{row['generic']} — {row['brand']} ({row.get('dosage_form','')} {row.get('dose','')})")
                    with c2:
                        newqty = st.number_input(f"Stock for #{idx}", min_value=0, value=int(row["stock_qty"]), key=f"stockedit_{idx}")
                        editable.at[idx, "stock_qty"] = int(newqty)
                    with c3:
                        st.write(f"Expiry: {row.get('expiry','')}")
                if st.button("Save Stock Changes"):
                    st.session_state["stock_df"] = editable.copy()
                    save_stock(st.session_state["stock_df"])
                    st.success("Stock saved to database.")

            # Dispense for patient: load patients and their visits
            conn = get_connection()
            patients_df = pd.read_sql("SELECT * FROM patients", conn)
            if patients_df.empty:
                conn.close()
                st.info("No patient records found. Save a patient record first in Patient Entry tab.")
            else:
                # select patient
                patient_ids = patients_df["patient_id"].tolist()
                selected_patient = st.selectbox("Select Patient ID to Dispense For", options=[""] + patient_ids, index=0)
                if selected_patient:
                    # load visits for this patient (most recent first)
                    visits_df = pd.read_sql(
                        "SELECT visit_id, visit_date, doctor_type, medicines, dispensed FROM visits WHERE patient_id=%s ORDER BY visit_date DESC",
                        conn, params=(int(selected_patient),)
                    )
                    if visits_df.empty:
                        st.info("No visits found for this patient. Ask doctor to save visit with medicines.")
                    else:
                        # allow filter: pending/ all / dispensed
                        filter_mode = st.radio("Show visits:", ["Pending (not dispensed)", "All", "Dispensed"], index=0, horizontal=True)
                        if filter_mode == "Pending (not dispensed)":
                            view_df = visits_df[visits_df["dispensed"].fillna("No") != "Yes"]
                        elif filter_mode == "Dispensed":
                            view_df = visits_df[visits_df["dispensed"].fillna("No") == "Yes"]
                        else:
                            view_df = visits_df

                        # present visits to choose from
                        visit_options = [f"{int(r.visit_id)} — {r.visit_date} ({r.doctor_type})" for r in view_df.itertuples()] if not view_df.empty else []
                        selected_visit_label = st.selectbox("Select Visit", options=[""] + visit_options, index=0)
                        if selected_visit_label:
                            visit_id = int(selected_visit_label.split(" — ")[0])
                            visit_row = view_df[view_df["visit_id"] == visit_id].iloc[0]
                            # read medicines text from visit (not patients)
                            raw_meds = str(visit_row.get("medicines", "")).split(";")
                            st.subheader(f"Medicines prescribed for visit {visit_id}")
                            dispense_plan = []

                            for i, raw in enumerate(raw_meds):
                                med_text = raw.strip()
                                if med_text == "":
                                    continue
                                brand_match = re.search(r"\[([^\]]+)\]", med_text)
                                brand = brand_match.group(1).strip() if brand_match else ""
                                generic = med_text.split("[")[0].strip()
                                generic_norm = generic.lower()

                                # find brands for this generic
                                possible_brands = stock_df[stock_df["generic"].str.lower() == generic_norm]
                                brand_options = possible_brands["brand"].unique().tolist()

                                selected_brand = ""
                                if len(brand_options) > 1:
                                    selected_brand = st.selectbox(
                                        f"Select brand for {generic} ({i+1})",
                                        options=brand_options,
                                        key=f"brand_select_{visit_id}_{i}"
                                    )
                                elif len(brand_options) == 1:
                                    selected_brand = brand_options[0]
                                else:
                                    selected_brand = brand  # fallback if none found

                                matched = stock_df[
                                    (stock_df["generic"].str.strip().str.lower() == generic_norm) &
                                    (stock_df["brand"].str.strip().str.lower() == selected_brand.lower())
                                    ]

                                stock_qty = int(matched.iloc[0]["stock_qty"]) if not matched.empty else 0
                                display_name = matched.iloc[0]["generic"] + " — " + matched.iloc[0]["brand"] if not matched.empty else generic

                                prescribed_match = re.search(r"\(([^)]*)\)", med_text)
                                prescribed_amount = ""
                                if prescribed_match:
                                    parts = prescribed_match.group(1).split(",")
                                    if len(parts) == 3:
                                        prescribed_amount = parts[2].strip()

                                c1,c2,c3,c4,c5,c6,c7 = st.columns([3,1,1,1,1,1,1])
                                with c1: st.write(display_name)
                                with c2: st.write(generic)
                                with c3: st.write(selected_brand)
                                with c4: st.write(stock_qty)
                                with c5: st.write(prescribed_amount)
                                with c6:
                                    qty_to_dispense = st.number_input(
                                        f"Dispense units for {i}",
                                        min_value=0,
                                        max_value=stock_qty,
                                        value=0,
                                        step=1,
                                        key=f"dispense_input_{visit_id}_{i}"
                                    )
                                with c7:
                                    st.write(f"Remaining: {stock_qty - qty_to_dispense}")

                                dispense_plan.append({
                                    "raw": med_text,
                                    "display": display_name,
                                    "generic": generic,
                                    "brand": selected_brand,
                                    "stock_qty": stock_qty,
                                    "dispense_qty": int(qty_to_dispense),
                                    "matched_index": matched.index[0] if not matched.empty else None
                                })

                            if st.button("Confirm Dispensation for Selected Visit"):
                                to_dispense = [d for d in dispense_plan if d["dispense_qty"] > 0]
                                if not to_dispense:
                                    st.warning("No dispense quantities greater than zero selected.")
                                else:
                                    updated_stock = stock_df.copy()
                                    dispensed_summary = []
                                    for d in to_dispense:
                                        qty = d["dispense_qty"]
                                        if d["matched_index"] is not None:
                                            idx = d["matched_index"]
                                            updated_stock.at[idx, "stock_qty"] -= qty
                                            new_stock_val = updated_stock.at[idx, "stock_qty"]
                                        else:
                                            st.error(f"Cannot dispense {d['display']}: no stock entry found.")
                                            continue
                                        dispensed_summary.append({
                                            "Medicine": d["display"],
                                            "Generic": d["generic"],
                                            "Brand": d["brand"],
                                            "QuantityDispensed": qty,
                                            "RemainingStock": new_stock_val
                                        })

                                    # save updated stock
                                    st.session_state["stock_df"] = updated_stock.copy()
                                    save_stock(updated_stock)
                                    refresh_stock()

                                    # update visits table (not patients)
                                    conn.cursor().execute(
                                        "UPDATE visits SET dispensed='Yes', dispensed_details=%s WHERE visit_id=%s",
                                        ("; ".join([f"{s['Medicine']} => {s['QuantityDispensed']} (remaining {s['RemainingStock']})" for s in dispensed_summary]), visit_id)
                                    )
                                    conn.commit()
                                    conn.close()

                                    st.success("Dispensation recorded and stock updated.")
                                    st.subheader("Dispensed summary")
                                    st.table(pd.DataFrame(dispensed_summary))



if __name__ == "__main__":
    # allow running main_app.py directly for debugging (will require authentication)
    run_app()


#streamlit run C:\Users\Administrator\Desktop\DIAGNOSTIC\medical_camp.py