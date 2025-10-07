# main_app.py
import pandas as pd
import streamlit as st
import sqlite3
import os
import re

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None
if "username" not in st.session_state:
    st.session_state["username"] = ""

# --------- Config ----------
DB_FILE = "emr.db"
EXCEL_FILE = "ERR Drug Audit.csv"
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

def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    return conn
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

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # patients (extended with CNIC, nationality, address, phone, doctor_type)
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
        gender TEXT,
        age INTEGER,
        symptoms TEXT,
        indications TEXT,
        medicines TEXT,
        dispensed TEXT,
        dispensed_details TEXT
    )
    """)
    # stock table
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

# initialize DB on import
init_db()

# --------- Stock helpers ----------
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
            # CSV import failure should not crash the app
            print("Error importing CSV:", e)
    stock_df = pd.read_sql("SELECT * FROM stock", conn)
    conn.close()
    return stock_df

def save_stock(df):
    conn = get_connection()
    df.to_sql("stock", conn, if_exists="replace", index=False)
    conn.close()

# session stock init helper
if "stock_df" not in st.session_state:
    st.session_state["stock_df"] = load_stock()

def refresh_stock():
    conn = get_connection()
    latest_stock = pd.read_sql("SELECT * FROM stock", conn)
    conn.close()
    st.session_state["stock_df"] = latest_stock.copy()

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
            last = conn.execute("SELECT patient_id FROM patients ORDER BY ROWID DESC LIMIT 1").fetchone()
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
    if "Patient Entry" in tabs:
        with tab_objs[tabs.index("Patient Entry")]:
            st.header("Patient Information")
            # ensure stock is available in session
            if "stock_df" not in st.session_state:
                refresh_stock()
            stock_df = st.session_state["stock_df"]

            # Auto ID
            next_id = get_next_patient_id()
            st.text_input("Patient ID (auto)", value=next_id, key="p_patient_id", disabled=True)
            patient_id = st.session_state.get("p_patient_id", next_id)

            # Personal details
            st.subheader("Personal Details")
            col1, col2 = st.columns(2)
            with col1:
                patient_name = st.text_input("Patient Name", key="p_patient_name")
                cnic = st.text_input("CNIC", key="p_cnic")
                nationality = st.text_input("Nationality", key="p_nationality")
            with col2:
                address = st.text_area("Address", key="p_address")
                phone = st.text_input("Phone Number", key="p_phone")
                # Doctor type selection
                doctor_type = st.selectbox("Doctor Type", ["General Physician", "Gynecologist", "Pediatrician", "Dermatologist", "Others"], key="doctor_type")

            patient_history = st.text_area("History", key="p_history")

            st.subheader("Vitals")
            # Row 1: BP and Heart Rate
            col1, col2, col3 = st.columns(3)
            with col1:
                bp_sys = st.number_input("BP Systolic", min_value=0, step=1, key="bp_sys")
            with col2:
                bp_dia = st.number_input("BP Diastolic", min_value=0, step=1, key="bp_dia")
            with col3:
                heart_rate = st.number_input("Heart Rate (BPM)", min_value=0, step=1, key="heart_rate")

            # Row 2: Optional vitals
            col4, col5, col6, col7 = st.columns(4)
            with col4:
                sat_o2 = st.number_input("SatO2 (%)", min_value=0, max_value=100, step=1, key="sat_o2")
            with col5:
                temp = st.number_input("Temp (°C)", min_value=25.0, max_value=45.0, step=0.1, key="temp")
            with col6:
                rr = st.number_input("Respiration Rate (RR)", min_value=0, step=1, key="rr")
            with col7:
                blood_glucose = st.number_input("Blood Glucose (mg/dL)", min_value=0, step=1, key="blood_glucose")

            gender = st.selectbox("Select Gender", ["Male", "Female", "Other"], key="p_gender")
            age = st.number_input("Age", min_value=0, max_value=120, step=1, key="p_age")

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

            # --- Load ICD Diagnoses once from session state ---
            icd_df = st.session_state.get("icd_df")
            icd_df = st.session_state.get("icd_df")
            if icd_df is not None and not icd_df.empty and "Diagnosis" in icd_df.columns:
                diagnosis_options = icd_df["Diagnosis"].dropna().unique().tolist()
            else:
                st.warning("ICD diagnosis file not loaded or missing 'Diagnosis' column.")
            indications = []
            for i in range(1,5):
                selected_icd = st.selectbox(
                    f"Select ICD Diagnosis {i}",
                    options=[""] + diagnosis_options,
                    key=f"icd_diag_{i}"
                )

            # Medicines selection
            st.subheader("Medicines (Up to 10)")
            medicines = []
            for i in range(1, 11):
                st.markdown(f"**Medicine {i}**")
                med_options = stock_df["generic"].dropna().unique().tolist()
                sel_generic = st.selectbox(f"Pick medicine [{i}]", [""] + med_options, key=f"med_sel_{i}")
                if sel_generic:
                    row = stock_df[stock_df["generic"] == sel_generic].iloc[0]
                    generic = row["generic"]
                    brand = row["brand"]
                    form = row["dosage_form"]
                    dose = row["dose"]
                    expiry = row["expiry"]
                    stockqty = row["stock_qty"]
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

            if st.button("Save Patient Record"):
                # minimal validation
                if not patient_id or not patient_name:
                    st.error("Please ensure Patient ID and Patient Name are provided.")
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
                    placeholders = ", ".join(["?"]*len(record))
                    columns = ", ".join(record.keys())
                    values = list(record.values())
                    conn.cursor().execute(f"INSERT OR REPLACE INTO patients ({columns}) VALUES ({placeholders})", values)
                    conn.commit()
                    conn.close()
                    st.success("Patient record saved successfully!")
                    st.json(record)
                    # clear some keys so next id/autofill works
                    try:
                        del st.session_state["p_patient_name"]
                        del st.session_state["p_cnic"]
                    except Exception:
                        pass

    # ---------- PATIENT RECORDS TAB ----------
    if "Patient Records" in tabs:
        with tab_objs[tabs.index("Patient Records")]:
            st.header("Patient Records")
            conn = get_connection()
            records_df = pd.read_sql("SELECT * FROM patients", conn)
            conn.close()

            if records_df.empty:
                st.info("No patient records found. Save some records first.")
            else:
                # For doctors & admin -> editable, for pharmacy -> view-only
                if role in ["doctor", "admin"]:
                    edited_df = st.data_editor(records_df, num_rows="dynamic")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Update Records"):
                            conn = get_connection()
                            # replace table with edited data
                            edited_df.to_sql("patients", conn, if_exists="replace", index=False)
                            conn.close()
                            st.success("Records updated successfully!")
                    with col2:
                        del_id = st.selectbox("Select Patient ID to Delete", options=[""] + records_df["patient_id"].tolist(), index=0)
                        if st.button("Delete Record"):
                            if del_id:
                                conn = get_connection()
                                conn.cursor().execute("DELETE FROM patients WHERE patient_id=?", (del_id,))
                                conn.commit()
                                conn.close()
                                st.success(f"Record with Patient ID '{del_id}' deleted.")
                                st.rerun()
                    st.dataframe(records_df, use_container_width=True)
                else:
                    # pharmacy or others: view only
                    st.dataframe(records_df, use_container_width=True)

                # Statistics: patients per doctor type + total
                st.subheader("Statistics")
                try:
                    stats_df = records_df.groupby("doctor_type").size().reset_index(name="total_patients")
                    st.table(stats_df)
                    st.info(f"**Total patients treated by all doctors:** {int(stats_df['total_patients'].sum())}")
                except Exception:
                    st.write("No statistics available.")

    # ---------- PHARMACY DISPENSATION TAB ----------
    if "Pharmacy Dispensation" in tabs:
        with tab_objs[tabs.index("Pharmacy Dispensation")]:
            # pharmacist & admin allowed here
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

            # Dispense for patient
            conn = get_connection()
            patients_df = pd.read_sql("SELECT * FROM patients", conn)
            conn.close()
            if patients_df.empty:
                st.info("No patient records found. Save a patient record first in Patient Entry tab.")
            else:
                patient_ids = patients_df["patient_id"].tolist()
                selected_patient = st.selectbox("Select Patient ID to Dispense For", options=[""] + patient_ids, index=0)
                if selected_patient:
                    patient_row = patients_df[patients_df["patient_id"] == selected_patient].iloc[0]
                    st.subheader(f"Medicines prescribed for {patient_row['patient_name']}")
                    raw_meds = str(patient_row.get("medicines", "")).split(";")
                    dispense_plan = []

                    for i, raw in enumerate(raw_meds):
                        med_text = raw.strip()
                        if med_text == "":
                            continue
                        brand_match = re.search(r"\[([^\]]+)\]", med_text)
                        brand = brand_match.group(1).strip() if brand_match else ""
                        generic = med_text.split("[")[0].strip()
                        generic_norm = generic.lower()

                        # 🟩 NEW — find all brands for this generic
                        possible_brands = stock_df[stock_df["generic"].str.lower() == generic_norm]
                        brand_options = possible_brands["brand"].unique().tolist()

                        # 🟩 NEW — if more than one brand, ask pharmacist which one to use
                        selected_brand = ""
                        if len(brand_options) > 1:
                            selected_brand = st.selectbox(
                                f"Select brand for {generic} ({i+1})",
                                options=brand_options,
                                key=f"brand_select_{i}"
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
                                key=f"dispense_input_{i}"
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

                    if st.button("Confirm Dispensation for Selected Patient"):
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

                            st.session_state["stock_df"] = updated_stock.copy()
                            save_stock(updated_stock)
                            refresh_stock()

                            conn = get_connection()
                            dd = "; ".join([f"{s['Medicine']} => {s['QuantityDispensed']} (remaining {s['RemainingStock']})" for s in dispensed_summary])
                            conn.cursor().execute(
                                "UPDATE patients SET dispensed='Yes', dispensed_details=? WHERE patient_id=?",
                                (dd, selected_patient)
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