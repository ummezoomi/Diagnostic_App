# app_sqlite.py
import pandas as pd
import streamlit as st
import sqlite3
import os
import re

# --------- Config ----------
DB_FILE = "emr.db"  # SQLite database
EXCEL_FILE = "ERR Drug Audit.csv"  # initial stock Excel

st.set_page_config(layout="centered", page_title="Medical Camp EMR & Pharmacy")
st.title("Medical Camp EMR System")
st.write("Enter patient details, symptoms, possible indications, and prescribed medicines.")

# --------- Database helpers ----------
def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Patients tablestreamlit run C:\Users\Administrator\Desktop\DIAGNOSTIC\check.py
    c.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        patient_id TEXT PRIMARY KEY,
        patient_name TEXT,
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

# Initialize DB
init_db()

# --------- Stock helpers ----------
def load_stock():
    conn = get_connection()
    # Migrate CSV stock if stock table empty
    stock_count = pd.read_sql("SELECT COUNT(*) as cnt FROM stock", conn).iloc[0,0]
    if stock_count == 0 and os.path.exists(EXCEL_FILE):
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
    stock_df = pd.read_sql("SELECT * FROM stock", conn)
    conn.close()
    return stock_df

def save_stock(df):
    conn = get_connection()
    df.to_sql("stock", conn, if_exists="replace", index=False)
    conn.close()

# Initialize stock in session_state
if "stock_df" not in st.session_state:
    st.session_state["stock_df"] = load_stock()

def refresh_stock():
    """Refresh stock from database into session_state"""
    conn = get_connection()
    latest_stock = pd.read_sql("SELECT * FROM stock", conn)
    conn.close()
    st.session_state["stock_df"] = latest_stock.copy()

# --------- UI Tabs ----------
tab1, tab2, tab3 = st.tabs(["Patient Entry", "Patient Records", "Pharmacy Dispensation"])

# ---------------- TAB 1: Patient Entry ----------------
with tab1:
    st.header("Patient Information")
    if "stock_df" not in st.session_state:
        refresh_stock()
    stock_df = st.session_state["stock_df"]
    patient_id = st.text_input("Patient ID", key="p_patient_id")
    patient_name = st.text_input("Patient Name", key="p_patient_name")
    patient_history = st.text_area("History", key="p_history")

    st.subheader("Vitals")
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1: bp_sys = st.number_input("BP Systolic", min_value=0, step=1, key="bp_sys")
    with col_v2: bp_dia = st.number_input("BP Diastolic", min_value=0, step=1, key="bp_dia")
    with col_v3: heart_rate = st.number_input("Heart Rate (BPM)", min_value=0, step=1, key="heart_rate")

    gender = st.selectbox("Select Gender", ["Male", "Female"], key="p_gender")
    age = st.number_input("Age", min_value=0, max_value=120, step=1, key="p_age")

    st.subheader("Symptoms (Up to 8)")
    symptoms = []
    for i in range(1, 9):
        val = st.text_input(f"Symptom {i}", key=f"symptom_{i}")
        if val and val.strip():
            symptoms.append(val.strip())

    st.subheader("Possible Indications (Up to 4)")
    indications = []
    for i in range(1,5):
        val = st.text_input(f"Indication {i}", key=f"indication_{i}")
        if val and val.strip():
            indications.append(val.strip())

    # load stock for dropdowns
    stock_df = st.session_state["stock_df"]

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
            col1, col2, col3 = st.columns([1, 1, 1])
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
    if not patient_id or not patient_name:
        st.error("Please enter Patient ID and Patient Name.")
    else:
        record = {
            "patient_id": patient_id,
            "patient_name": patient_name,
            "history": patient_history,
            "bp": f"{bp_sys}/{bp_dia}",
            "heart_rate": heart_rate,
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

# ---------------- TAB 2: Patient Records ----------------
with tab2:
    st.header("Patient Records")
    conn = get_connection()
    records_df = pd.read_sql("SELECT * FROM patients", conn)
    conn.close()
    if not records_df.empty:
        edited_df = st.data_editor(records_df, num_rows="dynamic")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Update Records"):
                conn = get_connection()
                edited_df.to_sql("patients", conn, if_exists="replace", index=False)
                conn.close()
                st.success("Records updated successfully!")
        with col2:
            del_id = st.selectbox("Select Patient ID to Delete", options=[""]+records_df["patient_id"].tolist(), index=0)
            if st.button("Delete Record"):
                if del_id:
                    conn = get_connection()
                    conn.cursor().execute("DELETE FROM patients WHERE patient_id=?", (del_id,))
                    conn.commit()
                    conn.close()
                    st.success(f"Record with Patient ID '{del_id}' deleted.")
                    st.experimental_rerun()
        st.dataframe(records_df, use_container_width=True)
    else:
        st.info("No patient records found. Save some records first.")

# ---------------- TAB 3: Pharmacy Dispensation ----------------
# ---------------- TAB 3: Pharmacy Dispensation ----------------
with tab3:
    st.header("Pharmacy Dispensation")
    # --- REFRESH STOCK BUTTON ---
    if st.button("🔄 Refresh Stock"):
        refresh_stock()
        st.success("Stock refreshed from database.")

    # Load stock from session
    stock_df = st.session_state["stock_df"]
    st.write("DEBUG STOCK:", stock_df[["generic","brand","stock_qty"]])

    # Stock Management
    with st.expander("🔧 Stock Management (view / quick edit)"):
        st.write("Update stock quantities. Saved to database.")
        editable = stock_df.copy()
        for idx, row in editable.iterrows():
            c1, c2, c3 = st.columns([4,1,1])
            with c1: st.write(f"{row['generic']} — {row['brand']} ({row['dosage_form']} {row['dose']})")
            with c2:
                newqty = st.number_input(f"Stock for #{idx}", min_value=0, value=int(row["stock_qty"]), key=f"stockedit_{idx}")
                editable.at[idx, "stock_qty"] = int(newqty)
            with c3: st.write(f"Expiry: {row.get('expiry','')}")
        if st.button("Save Stock Changes"):
            st.session_state["stock_df"] = editable.copy()
            save_stock(st.session_state["stock_df"])
            st.success("Stock saved to database.")

    # Dispense for patient
    conn = get_connection()
    patients_df = pd.read_sql("SELECT * FROM patients", conn)
    conn.close()
    if not patients_df.empty:
        patient_ids = patients_df["patient_id"].tolist()
        selected_patient = st.selectbox("Select Patient ID to Dispense For", options=[""] + patient_ids, index=0)
        if selected_patient:
            patient_row = patients_df[patients_df["patient_id"] == selected_patient].iloc[0]
            st.subheader(f"Medicines prescribed for {patient_row['patient_name']}")
            raw_meds = str(patient_row.get("medicines","")).split(";")
            dispense_plan = []

            for i, raw in enumerate(raw_meds):
                med_text = raw.strip()
                if med_text == "": continue
                brand_match = re.search(r"\[([^\]]+)\]", med_text)
                brand = brand_match.group(1).strip() if brand_match else ""
                generic = med_text.split("[")[0].strip()

                # Match stock
                generic_norm = generic.lower()
                brand_norm = brand.lower()
                matched = stock_df[
                    (stock_df["generic"].str.strip().str.lower() == generic_norm) &
                    (stock_df["brand"].str.strip().str.lower() == brand_norm)
                    ]
                if matched.empty:
                    matched = stock_df[stock_df["generic"].str.lower() == generic_norm] if generic else pd.DataFrame()

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
                with c3: st.write(brand)
                with c4: st.write(stock_qty)
                with c5: st.write(prescribed_amount)
                with c6:
                    qty_to_dispense = st.number_input(f"Dispense units for {i}", min_value=0, max_value=stock_qty, value=0, step=1, key=f"dispense_input_{i}")
                with c7: st.write(f"Remaining: {stock_qty - qty_to_dispense}")

                dispense_plan.append({
                    "raw": med_text,
                    "display": display_name,
                    "generic": generic,
                    "brand": brand,
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

                    # Save updated stock to session and SQLite
                    st.session_state["stock_df"] = updated_stock.copy()
                    save_stock(updated_stock)
                    refresh_stock()
                    # Update patient record in DB
                    conn = get_connection()
                    dd = "; ".join([f"{s['Medicine']} => {s['QuantityDispensed']} (remaining {s['RemainingStock']})" for s in dispensed_summary])
                    conn.cursor().execute("UPDATE patients SET dispensed='Yes', dispensed_details=? WHERE patient_id=?", (dd, selected_patient))
                    conn.commit()
                    conn.close()

                    st.success("Dispensation recorded and stock updated.")
                    st.subheader("Dispensed summary")
                    st.table(pd.DataFrame(dispensed_summary))
    else:
        st.info("No patient records found. Save a patient record first in Patient Entry tab.")

