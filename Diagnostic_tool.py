import pandas as pd
import streamlit as st
import sqlite3
import os
import re

# ---------- SESSION STATE ----------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None
if "username" not in st.session_state:
    st.session_state["username"] = ""

# ---------- CONFIG ----------
DB_FILE = "emr.db"
EXCEL_FILE = "ERR Drug Audit.csv"

# ---------- DATABASE CONNECTION ----------
def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    return conn

# ---------- LOAD ICD DATA ----------
def load_icd_diagnosis():
    try:
        df = pd.read_csv("icd_diagnosis.csv")
        if "Diagnosis" not in df.columns:
            st.warning("ICD file missing 'Diagnosis' column.")
            df = pd.DataFrame(columns=["Diagnosis"])
        return df
    except Exception as e:
        st.error(f"Error loading ICD diagnosis file: {e}")
        return pd.DataFrame(columns=["Diagnosis"])

def load_icd_symptoms():
    try:
        df = pd.read_csv("ICD10_Symptom_List_All.csv")
        if "Symptom" not in df.columns or "Body_System" not in df.columns:
            st.warning("Symptom file missing 'Symptom' or 'Body_System' column.")
            df = pd.DataFrame(columns=["Symptom", "Body_System"])
        return df
    except Exception as e:
        st.error(f"Error loading ICD symptoms file: {e}")
        return pd.DataFrame(columns=["Symptom", "Body_System"])

if "icd_df" not in st.session_state:
    st.session_state["icd_df"] = load_icd_diagnosis()
if "icd_symptoms_df" not in st.session_state:
    st.session_state["icd_symptoms_df"] = load_icd_symptoms()

# ---------- DATABASE INITIALIZATION ----------
def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Patients table
    c.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id TEXT PRIMARY KEY,
            patient_name TEXT,
            cnic TEXT,
            nationality TEXT,
            address TEXT,
            phone TEXT,
            doctor_type TEXT,
            history TEXT,
            bp TEXT,
            heart_rate INTEGER,
            sat_o2 REAL,
            temp REAL,
            rr INTEGER,
            blood_glucose REAL,
            gender TEXT,
            age INTEGER,
            symptoms TEXT,
            indications TEXT,
            medicines TEXT,
            dispensed TEXT,
            dispensed_details TEXT
        )
    """)
    # Stock table
    c.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            key TEXT PRIMARY KEY,
            generic TEXT,
            brand TEXT,
            dosage_form TEXT,
            dose TEXT,
            expiry TEXT,
            unit TEXT,
            stock_qty INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- STOCK FUNCTIONS ----------
def load_stock():
    conn = get_connection()
    try:
        stock_count = pd.read_sql("SELECT COUNT(*) as cnt FROM stock", conn).iloc[0,0]
    except Exception:
        stock_count = 0
    if stock_count == 0 and os.path.exists(EXCEL_FILE):
        try:
            stock = pd.read_csv(EXCEL_FILE)
            stock.columns = stock.columns.str.strip()
            stock["StockQty"] = stock.get("Quantity", 0).fillna(0).astype(int)
            stock["Generic"] = stock["Generic"].fillna("").str.strip().str.title()
            stock["Brand"] = stock["Brand"].fillna("").str.strip().str.title()
            stock["Dosage Form"] = stock["Dosage Form"].fillna("").str.strip().str.title()
            stock["Dose"] = stock["Dose"].fillna("").str.strip()
            stock["Expiry"] = stock["Expiry"].fillna("").str.strip()
            stock["Unit"] = stock.get("Unit","").fillna("").str.strip().str.lower()
            stock = stock[(stock["Generic"]!="") | (stock["Brand"]!="")].copy()
            stock["Key"] = stock["Generic"].str.lower() + "||" + stock["Brand"].str.lower()
            conn.cursor().executemany("""
                INSERT OR REPLACE INTO stock (key,generic,brand,dosage_form,dose,expiry,unit,stock_qty)
                VALUES (?,?,?,?,?,?,?,?)
            """, stock[["Key","Generic","Brand","Dosage Form","Dose","Expiry","Unit","StockQty"]].values.tolist())
            conn.commit()
        except Exception as e:
            print("Error importing CSV:", e)
    stock_df = pd.read_sql("SELECT * FROM stock", conn)
    conn.close()
    return stock_df

def save_stock(df):
    conn = get_connection()
    df.to_sql("stock", conn, if_exists="replace", index=False)
    conn.close()

if "stock_df" not in st.session_state:
    st.session_state["stock_df"] = load_stock()

def refresh_stock():
    st.session_state["stock_df"] = pd.read_sql("SELECT * FROM stock", get_connection())

# ---------- APP ----------
def run_app():
    st.set_page_config(layout="centered", page_title="Medical Camp EMR & Pharmacy")
    auth = st.session_state.get("logged_in", False)
    role = st.session_state.get("role", None)
    username = st.session_state.get("username", "")

    if not auth:
        st.warning("Not authenticated. Go to login page.")
        st.stop()

    # Sidebar
    st.sidebar.markdown(f"**User:** {username}")
    st.sidebar.markdown(f"**Role:** {role}")
    if st.sidebar.button("Logout"):
        for key in ["logged_in","role","username"]:
            if key in st.session_state: del st.session_state[key]
        st.rerun()

    st.title("Medical Camp EMR System")

    # Role-based tabs
    tabs = []
    if role == "admin":
        tabs = ["Patient Entry", "Patient Records", "Pharmacy Dispensation"]
    elif role == "doctor":
        tabs = ["Patient Entry", "Patient Records"]
    elif role == "pharmacy":
        tabs = ["Pharmacy Dispensation", "Patient Records"]
    else:
        st.error("Unknown role")
        st.stop()

    tab_objs = st.tabs(tabs)

    # ---------- NEXT PATIENT ID ----------
    def get_next_patient_id():
        conn = get_connection()
        try:
            last = conn.execute("SELECT patient_id FROM patients ORDER BY ROWID DESC LIMIT 1").fetchone()
            conn.close()
            return str(int(last[0])+1) if last else "1"
        except:
            conn.close()
            return str(int(pd.Timestamp.now().timestamp()))

    # ---------- PATIENT ENTRY ----------
    if "Patient Entry" in tabs:
        with tab_objs[tabs.index("Patient Entry")]:
            st.header("Patient Information")
            stock_df = st.session_state["stock_df"]
            next_id = get_next_patient_id()
            st.text_input("Patient ID (auto)", value=next_id, key="p_patient_id", disabled=True)
            patient_id = st.session_state.get("p_patient_id", next_id)

            # Personal Details
            st.subheader("Personal Details")
            col1, col2 = st.columns(2)
            with col1:
                patient_name = st.text_input("Patient Name", key="p_patient_name")
                cnic = st.text_input("CNIC", key="p_cnic")
                nationality = st.text_input("Nationality", key="p_nationality")
            with col2:
                address = st.text_area("Address", key="p_address")
                phone = st.text_input("Phone Number", key="p_phone")
                doctor_type = st.selectbox("Doctor Type", ["General Physician","Gynecologist","Pediatrician","Dermatologist","Others"], key="doctor_type")
            patient_history = st.text_area("History", key="p_history")

            # Vitals
            st.subheader("Vitals")
            col1,col2,col3 = st.columns(3)
            bp_sys = col1.number_input("BP Systolic", min_value=0, step=1, key="bp_sys")
            bp_dia = col2.number_input("BP Diastolic", min_value=0, step=1, key="bp_dia")
            heart_rate = col3.number_input("Heart Rate", min_value=0, step=1, key="heart_rate")
            col4,col5,col6,col7 = st.columns(4)
            sat_o2 = col4.number_input("SatO2", min_value=0, max_value=100, step=1, key="sat_o2")
            temp = col5.number_input("Temp", min_value=25.0, max_value=45.0, step=0.1, key="temp")
            rr = col6.number_input("Respiration Rate", min_value=0, step=1, key="rr")
            blood_glucose = col7.number_input("Blood Glucose", min_value=0, step=1, key="blood_glucose")
            gender = st.selectbox("Gender", ["Male","Female","Other"], key="p_gender")
            age = st.number_input("Age", min_value=0, max_value=120, step=1, key="p_age")

            # Symptoms
            st.subheader("Symptoms (Up to 8)")
            symptoms = []
            symptom_options = st.session_state["icd_symptoms_df"]["Symptom"].dropna().unique().tolist()
            for i in range(1,9):
                sel = st.selectbox(f"Symptom {i}", options=[""]+symptom_options, key=f"symptom_{i}")
                if sel: symptoms.append(sel)

            # ICD Diagnoses
            st.subheader("Possible Indications (Up to 4)")
            indications = []
            diagnosis_options = st.session_state["icd_df"]["Diagnosis"].dropna().unique().tolist()
            for i in range(1,5):
                sel_diag = st.selectbox(f"ICD Diagnosis {i}", options=[""]+diagnosis_options, key=f"icd_diag_{i}")
                if sel_diag: indications.append(sel_diag)

            # Medicines
            st.subheader("Medicines (Up to 10)")
            medicines = []
            for i in range(1,11):
                st.markdown(f"**Medicine {i}**")
                med_options = stock_df["generic"].dropna().unique().tolist()
                sel_generic = st.selectbox(f"Pick medicine [{i}]", [""]+med_options, key=f"med_sel_{i}")
                if sel_generic:
                    row = stock_df[stock_df["generic"] == sel_generic].iloc[0]
                    col1,col2,col3 = st.columns([1,1,1])
                    with col1: freq = st.text_input(f"Frequency [{i}]", key=f"med_freq_{i}", label_visibility="collapsed")
                    with col2: time_day = st.text_input(f"Time [{i}]", key=f"med_time_{i}", label_visibility="collapsed")
                    with col3: amount = st.text_input(f"Amount [{i}]", key=f"med_amount_{i}", label_visibility="collapsed")
                    medicines.append({
                        "generic": row["generic"], "brand": row["brand"], "form": row["dosage_form"],
                        "dose": row["dose"], "expiry": row["expiry"], "stock_qty": row["stock_qty"],
                        "frequency": freq.strip(), "time": time_day.strip(), "amount": amount.strip()
                    })

            if st.button("Save Patient Record"):
                if not patient_name:
                    st.error("Patient Name required.")
                else:
                    record = {
                        "patient_id": patient_id,
                        "patient_name": patient_name,
                        "cnic": cnic,
                        "nationality": nationality,
                        "address": address,
                        "phone": phone,
                        "doctor_type": doctor_type,
                        "history": patient_history,
                        "bp": f"{bp_sys}/{bp_dia}",
                        "heart_rate": heart_rate,
                        "sat_o2": sat_o2,
                        "temp": temp,
                        "rr": rr,
                        "blood_glucose": blood_glucose,
                        "gender": gender,
                        "age": age,
                        "symptoms": "; ".join(symptoms),
                        "indications": "; ".join(indications),
                        "medicines": "; ".join([f"{m['generic']} [{m['brand']}] ({m['frequency']}, {m['time']}, {m['amount']})" for m in medicines]),
                        "dispensed": "No",
                        "dispensed_details": ""
                    }
                    conn = get_connection()
                    placeholders = ",".join(["?"]*len(record))
                    columns = ",".join(record.keys())
                    values = list(record.values())
                    conn.cursor().execute(f"INSERT OR REPLACE INTO patients ({columns}) VALUES ({placeholders})", values)
                    conn.commit()
                    conn.close()
                    st.success("Patient record saved!")
                    st.json(record)

    # ---------- PATIENT RECORDS TAB ----------
    if "Patient Records" in tabs:
        with tab_objs[tabs.index("Patient Records")]:
            st.header("Patient Records")
            conn = get_connection()
            records_df = pd.read_sql("SELECT * FROM patients", conn)
            conn.close()
            if records_df.empty:
                st.info("No patient records.")
            else:
                st.dataframe(records_df, use_container_width=True)

    # ---------- PHARMACY DISPENSATION TAB ----------
    if "Pharmacy Dispensation" in tabs:
        with tab_objs[tabs.index("Pharmacy Dispensation")]:
            st.header("Pharmacy Dispensation")
            if st.button("🔄 Refresh Stock"):
                refresh_stock()
                st.success("Stock refreshed.")
            stock_df = st.session_state["stock_df"]

            # Select patient
            conn = get_connection()
            patient_list = pd.read_sql("SELECT patient_id, patient_name, medicines, dispensed FROM patients", conn)
            conn.close()
            if patient_list.empty:
                st.info("No patients found.")
            else:
                patient_selected = st.selectbox("Select Patient", options=[""] + patient_list["patient_id"].tolist())
                if patient_selected:
                    patient_row = patient_list[patient_list["patient_id"]==patient_selected].iloc[0]
                    st.subheader(f"Patient: {patient_row['patient_name']}")
                    st.markdown(f"**Medicines Prescribed:**")
                    meds = patient_row["medicines"].split("; ") if patient_row["medicines"] else []
                    dispensed_details = []
                    for med in meds:
                        st.markdown(f"- {med}")
                        generic_match = re.findall(r"^([^\[]+)", med)
                        if generic_match:
                            generic_name = generic_match[0].strip()
                            stock_options = stock_df[stock_df["generic"]==generic_name]
                            if not stock_options.empty:
                                stock_row = stock_options.iloc[0]
                                qty_dispensed = st.number_input(f"Dispense quantity for {generic_name}", min_value=0, max_value=int(stock_row["stock_qty"]), key=f"disp_{generic_name}")
                                if qty_dispensed > 0:
                                    dispensed_details.append(f"{generic_name} - {qty_dispensed} units")
                                    # Update stock
                                    new_qty = int(stock_row["stock_qty"]) - int(qty_dispensed)
                                    conn = get_connection()
                                    conn.execute("UPDATE stock SET stock_qty=? WHERE key=?", (new_qty, stock_row["key"]))
                                    conn.commit()
                                    conn.close()
                    if st.button("Confirm Dispensation"):
                        conn = get_connection()
                        conn.execute("UPDATE patients SET dispensed='Yes', dispensed_details=? WHERE patient_id=?",
                                     ("; ".join(dispensed_details), patient_selected))
                        conn.commit()
                        conn.close()
                        refresh_stock()
                        st.success("Dispensation completed and stock updated!")

if __name__ == "__main__":
    run_app()
