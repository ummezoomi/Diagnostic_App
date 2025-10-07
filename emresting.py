import sqlite3
import pandas as pd
import streamlit as st
import os
import re

# --------- Config / filenames ----------
EXCEL_FILE = "ERR Drug Audit.csv"      # Original stock Excel
SAVE_FILE = "UmerEMR_records.csv.csv"      # Patient records
STOCK_FILE = "medicine_stock.csv"      # Updated stock after dispensing

st.set_page_config(layout="centered", page_title="Medical Camp EMR & Pharmacy")
st.title("Medical Camp EMR System")
st.write("Enter patient details, symptoms, possible indications, and prescribed medicines.")


# --------- Helper: load + normalize stock ----------
@st.cache_data(ttl=300)
def load_stock():
    """Load stock from medicine_stock.csv if exists, else from Excel"""
    if os.path.exists(STOCK_FILE):
        stock = pd.read_csv(STOCK_FILE)
    else:
        stock = pd.read_csv(EXCEL_FILE)

    stock.columns = stock.columns.str.strip()

    # Normalize
    if os.path.exists(STOCK_FILE):
        # Loaded from saved stock CSV
        if "StockQty" not in stock.columns:
            stock["StockQty"] = stock.get("Quantity", 0).fillna(0).astype(int)
        else:
            stock["StockQty"] = stock["StockQty"].fillna(0).astype(int)
    else:
    # Loaded from original Excel
        stock["StockQty"] = stock.get("Quantity", 0).fillna(0).astype(int)

    stock["Generic"] = stock["Generic"].fillna("").str.strip().str.title()
    stock["Brand"] = stock["Brand"].fillna("").str.strip().str.title()
    stock["Dosage Form"] = stock["Dosage Form"].fillna("").str.strip().str.title()
    stock["Dose"] = stock["Dose"].fillna("").str.strip()
    stock["Expiry"] = stock["Expiry"].fillna("").str.strip()
    stock["Unit"] = stock.get("Unit", "").fillna("").str.strip().str.lower()

    # Drop empty rows
    stock = stock[(stock["Generic"] != "") | (stock["Brand"] != "")].copy()

    # Build Key + Display
    stock["Key"] = stock["Generic"].str.lower() + "||" + stock["Brand"].str.lower()
    stock["Display"] = stock.apply(
        lambda r: f"{r['Generic']} — {r['Brand']} ({r['Dosage Form']} {r['Dose']})".strip(),
        axis=1
    )

    # Aggregate duplicates
    agg = stock.groupby(
        ["Key","Display","Generic","Brand","Dosage Form","Dose","Expiry","Unit"],
        dropna=False, as_index=False
    )["StockQty"].sum()
    cols_to_show = ["Generic", "Brand", "StockQty"]
    if "Quantity" in stock.columns:
        cols_to_show.insert(2, "Quantity")  # Show Quantity if present
    return agg.reset_index(drop=True)

# Initialize stock in session_state if not already present
if "stock_df" not in st.session_state:
    st.session_state["stock_df"] = load_stock()

# Save stock only
def save_stock(df):
    df.to_csv(STOCK_FILE, index=False)

# --------- UI Tabs ----------
tab1, tab2, tab3 = st.tabs(["Patient Entry", "Patient Records", "Pharmacy Dispensation"])

# ---------------- TAB 1: Patient Entry ----------------
with tab1:
    st.header("Patient Information")
    patient_id = st.text_input("Patient ID", key="p_patient_id")
    patient_name = st.text_input("Patient Name", key="p_patient_name")
    patient_history = st.text_area("History", key="p_history")

    st.subheader("Vitals")
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        bp_sys = st.number_input("BP Systolic", min_value=0, step=1, key="bp_sys")
    with col_v2:
        bp_dia = st.number_input("BP Diastolic", min_value=0, step=1, key="bp_dia")
    with col_v3:
        heart_rate = st.number_input("Heart Rate (BPM)", min_value=0, step=1, key="heart_rate")

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
    for i in range(1, 5):
        val = st.text_input(f"Indication {i}", key=f"indication_{i}")
        if val and val.strip():
            indications.append(val.strip())

    # load stock to provide dropdown options
    stock_df = st.session_state["stock_df"]

    st.subheader("Medicines (Up to 10)")
    medicines = []
    for i in range(1, 11):
        st.markdown(f"**Medicine {i}**")
        med_options = stock_df["Generic"].dropna().unique().tolist()
        sel_generic = st.selectbox(
            f"Pick medicine [{i}]",
            [""] + med_options,
            key=f"med_sel_{i}"
        )
        if sel_generic:
            row = stock_df[stock_df["Generic"] == sel_generic].iloc[0]
            generic = row["Generic"]
            brand = row["Brand"]
            form = row["Dosage Form"]
            dose = row["Dose"]
            expiry = row["Expiry"]
            stockqty = row["StockQty"]
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                freq = st.text_input(f"Frequency [{i}]", key=f"med_freq_{i}", label_visibility="collapsed", placeholder="Frequency")
            with col2:
                time_day = st.text_input(f"Time [{i}]", key=f"med_time_{i}", label_visibility="collapsed", placeholder="Time of Day")
            with col3:
                amount = st.text_input(f"Amount [{i}]", key=f"med_amount_{i}", label_visibility="collapsed", placeholder="Amount")
            st.caption(f"Brand: {brand}, Form: {form}, Dose: {dose}, Expiry: {expiry}, Stock: {stockqty}")
            medicines.append({
                "Generic": generic,
                "Brand": brand,
                "Form": form,
                "Dose": dose,
                "Expiry": expiry,
                "StockQty": stockqty,
                "Frequency": freq.strip(),
                "Time": time_day.strip(),
                "Amount": amount.strip()
            })

if st.button("Save Patient Record"):
    if not patient_id or not patient_name:
        st.error("Please enter Patient ID and Patient Name.")
    elif not symptoms and not indications and not medicines:
        st.error("Please enter at least one symptom, indication, or medicine.")
    else:
        record = {
            "Patient ID": str(patient_id),
            "Patient Name": patient_name,
            "History": patient_history,
            "BP": f"{bp_sys}/{bp_dia}",
            "Heart Rate": heart_rate,
            "Gender": gender,
            "Age": age,
            "Symptoms": "; ".join(symptoms),
            "Indications": "; ".join(indications),
            "Medicines": "; ".join([f"{m['Generic']} [{m['Brand']}] ({m['Frequency']}, {m['Time']}, {m['Amount']})" for m in medicines]),
            "Dispensed": "No",
            "Dispensed Details": ""
        }
        if os.path.exists(SAVE_FILE):
            saved_df = pd.read_csv(SAVE_FILE, dtype=str).fillna("")
            if str(patient_id) in saved_df["Patient ID"].astype(str).values:
                saved_df.loc[saved_df["Patient ID"].astype(str) == str(patient_id), list(record.keys())] = list(record.values())
            else:
                saved_df = pd.concat([saved_df, pd.DataFrame([record])], ignore_index=True)
        else:
            saved_df = pd.DataFrame([record])
        saved_df.to_csv(SAVE_FILE, index=False)
        st.success("Patient record saved successfully!")
        st.subheader("Saved Patient Record")
        st.json(record)

# ---------------- TAB 2: Patient Records ----------------
with tab2:
    st.header("Patient Records")
    if os.path.exists(SAVE_FILE):
        records_df = pd.read_csv(SAVE_FILE, dtype=str).fillna("")
        edited_df = st.data_editor(records_df, num_rows="dynamic")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Update Records"):
                edited_df.to_csv(SAVE_FILE, index=False)
                st.success("Records updated successfully!")
        with col2:
            patient_ids = records_df["Patient ID"].tolist()
            del_id = st.selectbox("Select Patient ID to Delete", options=[""] + patient_ids, index=0)
            if st.button("Delete Record"):
                if del_id == "":
                    st.warning("Please select a Patient ID to delete.")
                else:
                    new_df = records_df[records_df["Patient ID"] != del_id]
                    new_df.to_csv(SAVE_FILE, index=False)
                    st.success(f"Record with Patient ID '{del_id}' deleted.")
                    st.experimental_rerun()
        st.subheader("All Patient Records")
        st.dataframe(records_df, use_container_width=True)
    else:
        st.info("No patient records found. Save some records in the 'Patient Entry' tab first.")

# ---------------- TAB 3: Pharmacy Dispensation ----------------
with tab3:
    st.header("Pharmacy Dispensation")

    # Load stock
    stock_df = st.session_state["stock_df"]
    st.write("Stock loaded")

    st.write("CURRENT STOCK", stock_df[["Generic","Brand","StockQty"]])
    # Stock Management
    with st.expander("🔧 Stock Management (view / quick edit)"):
        st.write("Update stock quantities. Saved to `medicine_stock.csv`.")
        editable = stock_df.copy()
        for idx, row in editable.iterrows():
            c1, c2, c3 = st.columns([4, 1, 1])
            with c1: st.write(row["Display"])
            with c2:
                newqty = st.number_input(f"Stock for #{idx}", min_value=0, value=int(row["StockQty"]), key=f"stockedit_{idx}")
                editable.at[idx, "StockQty"] = int(newqty)
            with c3: st.write(f"Expiry: {row.get('Expiry','')}")
        if st.button("Save Stock Changes"):
            st.session_state["stock_df"] = editable.copy()  # update session state
            save_stock(st.session_state["stock_df"])       # save to CSV
            st.success("Stock saved.")

    # Dispense for patient
    if os.path.exists(SAVE_FILE):
        patients_df = pd.read_csv(SAVE_FILE, dtype=str).fillna("")
        patient_ids = patients_df["Patient ID"].tolist()
        selected_patient = st.selectbox("Select Patient ID to Dispense For", options=[""] + patient_ids, index=0)

        if selected_patient:
            patient_row = patients_df[patients_df["Patient ID"] == selected_patient].iloc[0]
            st.subheader(f"Medicines prescribed for {patient_row['Patient Name']}")
            raw_meds = str(patient_row.get("Medicines", "")).split(";")
            dispense_plan = []
            for i, raw in enumerate(raw_meds):
                med_text = raw.strip()
                if med_text == "": continue
                brand_match = re.search(r"\[([^\]]+)\]", med_text)
                brand = brand_match.group(1).strip() if brand_match else ""

                generic = med_text.split("[")[0].strip()
                brand = brand_match.group(1).strip() if brand_match else ""
                generic_norm = generic.lower()
                brand_norm = brand.lower()
                matched = stock_df[
                    (stock_df["Generic"].str.strip().str.lower() == generic_norm) &
                    (stock_df["Brand"].str.strip().str.lower() == brand_norm)
                    ]
                if matched.empty:
                    matched = stock_df[stock_df["Generic"].str.lower() == generic_norm] if generic else pd.DataFrame()
                stock_qty = int(matched.iloc[0]["StockQty"]) if not matched.empty else 0
                display_name = matched.iloc[0]["Display"] if not matched.empty else med_text.split("[")[0].strip()

                prescribed_match = re.search(r"\(([^)]*)\)", med_text)
                prescribed_amount = ""
                if prescribed_match:
                    # expected format: "(Frequency, Time, Amount)"
                    parts = prescribed_match.group(1).split(",")
                    if len(parts) == 3:
                        prescribed_amount = parts[2].strip()
                c1,c2,c3,c4,c5,c6, c7 = st.columns([3,1,1,1,1,1,1])
                with c1: st.write(display_name)
                with c2: st.write(generic)
                with c3: st.write(brand)
                with c4: st.write(stock_qty)
                with c5: st.write(prescribed_amount)
                with c6: qty_to_dispense = st.number_input(f"Dispense units for {i}", min_value=0, max_value=stock_qty, value=0, step=1, key=f"dispense_input_{i}")
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
                    updated_stock = st.session_state["stock_df"].copy()
                    dispensed_summary = []
                    for d in to_dispense:
                        qty = d["dispense_qty"]
                        if d["matched_index"] is not None:
                            idx = d["matched_index"]
                            updated_stock.loc[updated_stock.index == idx, "StockQty"] -= qty
                            updated_stock.loc[updated_stock.index == idx, "Quantity"] = updated_stock.loc[updated_stock.index == idx, "StockQty"]
                            new_stock_val = int(updated_stock.loc[updated_stock.index == idx, "StockQty"].iloc[0])
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
                    save_stock(updated_stock)
                    patients_df.loc[patients_df["Patient ID"] == selected_patient, "Dispensed"] = "Yes"
                    dd = "; ".join([f"{s['Medicine']} => {s['QuantityDispensed']} (remaining {s['RemainingStock']})" for s in dispensed_summary])
                    patients_df.loc[patients_df["Patient ID"] == selected_patient, "Dispensed Details"] = dd
                    patients_df.to_csv(SAVE_FILE, index=False)
                    st.success("Dispensation recorded and stock updated.")
                    st.subheader("Dispensed summary")
                    st.table(pd.DataFrame(dispensed_summary))
                    st.session_state["stock_df"] = updated_stock.copy()
                    save_stock(st.session_state["stock_df"])
    else:
        st.info("No patient records found. Save a patient record first in Patient Entry tab.")
