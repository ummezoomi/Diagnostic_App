# app.py
import pandas as pd
import streamlit as st
import os
import re

# --------- Config / filenames ----------
EXCEL_FILE = "ERR Drug Audit.csv"          # keep this file in same folder
SAVE_FILE = "UmerEMR_records.csv.csv"       # your existing record file name

st.set_page_config(layout="centered", page_title="Medical Camp EMR & Pharmacy")
st.title("Medical Camp EMR System")
st.write("Enter patient details, symptoms, possible indications, and prescribed medicines.")

# --------- Helper: load + normalize stock from Excel ----------
@st.cache_data(ttl=300)
def load_stock(csv_path: str = EXCEL_FILE):
    """Load stock directly from ERR Drug Audit.csv and normalize"""
    stock = pd.read_csv(csv_path)

    # Normalize
    if os.path.exists(EXCEL_FILE):
        stock["StockQty"] = stock.get("Quantity", 0).fillna(0).astype(int)
    else:
        stock["StockQty"] = stock.get("StockQty", 0).fillna(0).astype(int)
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

    return agg.reset_index(drop=True)


# Load initial stock from Excel (this is the canonical source); if we persisted CSV already, prefer it for read+write
def save_stock(df):
    df.to_csv(EXCEL_FILE, index=False)

# --------- UI Tabs ----------
tab1, tab2, tab3 = st.tabs(["Patient Entry", "Patient Records", "Pharmacy Dispensation"])

# ---------------- TAB 1: Patient Entry (with medicine dropdown) ----------------
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
    stock_df = load_stock()

    st.subheader("Medicines (Up to 10)")
    medicines = []

    for i in range(1, 11):
        st.markdown(f"**Medicine {i}**")

        # Dropdown shows only GENERIC names
        med_options = stock_df["Generic"].dropna().unique().tolist()
        sel_generic = st.selectbox(
            f"Pick medicine [{i}]",
            [""] + med_options,
            key=f"med_sel_{i}"
        )

        if sel_generic:
            # Get the first matching stock row for that generic
            row = stock_df[stock_df["Generic"] == sel_generic].iloc[0]

            generic = row["Generic"]
            brand = row["Brand"]
            form = row["Dosage Form"]
            dose = row["Dose"]
            expiry = row["Expiry"]
            stockqty = row["StockQty"]

            # Compact layout for extra fields
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
                # Save medicines in consistent format: Display (Generic|Brand) -> for parsing later
                "Medicines": "; ".join([f"{m['Generic']} [{m['Brand']}] ({m['Frequency']}, {m['Time']}, {m['Amount']})" for m in medicines]),
                "Dispensed": "No",
                "Dispensed Details": ""
            }

            if os.path.exists(SAVE_FILE):
                saved_df = pd.read_csv(SAVE_FILE, dtype=str).fillna("")
                if str(patient_id) in saved_df["Patient ID"].astype(str).values:
                    # update existing row
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

# ---------------- TAB 3: Pharmacy Dispensation (Excel-based format) ----------------
with tab3:
    st.header("Pharmacy Dispensation (based on Baba Island sheet format)")

    # Load stocks (prefer persisted CSV if exists, otherwise Excel parse)
    stock_df = load_stock()  # this reads STOCK_FILE_CSV if exists else from excel
    st.write("Stock loaded")

    # allow pharmacist to add/update stock rows from UI
    with st.expander("🔧 Stock Management (view / quick edit)"):
        st.write("You can update stock quantities here. Changes will be saved to `medicine_stock.csv`.")
        editable = stock_df.copy()
        # show a simple table with edit inputs for StockQty
        for idx, row in editable.iterrows():
            c1, c2, c3 = st.columns([4, 1, 1])
            with c1:
                st.write(row["Display"])
            with c2:
                newqty = st.number_input(f"Stock for #{idx}", min_value=0, value=int(row["StockQty"]), key=f"stockedit_{idx}")
                editable.at[idx, "StockQty"] = int(newqty)
            with c3:
                st.write(f"Expiry: {row.get('Expiry','')}")
        if st.button("Save Stock Changes"):
            save_stock(editable)
            st.success("Stock saved to medicine_stock.csv")
            stock_df = editable.copy()

    # Pick a patient to dispense for
    if os.path.exists(SAVE_FILE):
        patients_df = pd.read_csv(SAVE_FILE, dtype=str).fillna("")
        patient_ids = patients_df["Patient ID"].tolist()
        selected_patient = st.selectbox("Select Patient ID to Dispense For", options=[""] + patient_ids, index=0)

        if selected_patient:
            patient_row = patients_df[patients_df["Patient ID"] == selected_patient].iloc[0]
            st.subheader(f"Medicines prescribed for {patient_row['Patient Name']}")

            # Parse prescribed medicines saved earlier:
            # Format example: "loratidine — lorgy (tab 10mg) [loratidine|lorgy] (2x/day, Morning, 10mg); ..."
            raw_meds = str(patient_row.get("Medicines", "")).split(";")
            # Build UI table rows
            dispense_plan = []
            for i, raw in enumerate(raw_meds):
                med_text = raw.strip()
                if med_text == "":
                    continue
                # Extract Display and Generic|Brand block if present
                # pattern: ... [generic|brand] (...) -> we'll try to extract [...|...]
                m_key = re.search(r"\[([^\]]+)\]", med_text)
                generic = ""
                brand = ""
                amount_match = re.search(r"\((?:[^)]*, ){2}([^)]+)\)", med_text)
                prescribed_amount = amount_match.group(1).strip() if amount_match else "N/A"
                if m_key:
                    parts = m_key.group(1).split("|")
                    generic = parts[0].strip() if len(parts) > 0 else ""
                    brand = parts[1].strip() if len(parts) > 1 else ""
                # Determine stock match by key:
                generic_norm = generic.strip().lower()
                brand_norm = brand.strip().lower()
                matched = stock_df[
                    (stock_df["Generic"].str.strip().str.lower() == generic_norm) &
                    (stock_df["Brand"].str.strip().str.lower() == brand_norm)
                ]

                if matched.empty:
                    # Try match by generic only
                    matched = stock_df[stock_df["Generic"].str.lower() == generic.lower()] if generic else pd.DataFrame()
                stock_qty = int(matched.iloc[0]["StockQty"]) if (not matched.empty) else 0
                display_name = matched.iloc[0]["Display"] if (not matched.empty) else med_text.split("[")[0].strip()

                # show row with stock and dispense input (max = stock_qty)
                c1, c2, c3, c4, c5, c6, c7= st.columns([3,1,1,1,1,1,1])
                with c1:
                    st.write(display_name)
                with c2:
                    st.write(generic)
                with c3:
                    st.write(brand)
                with c4:
                    st.write(stock_qty)
                with c5:
                    st.write(prescribed_amount)
                with c6:
                    qty_to_dispense = st.number_input(f"Dispense units for {i}", min_value=0, max_value=stock_qty, value=0, step=1, key=f"dispense_input_{i}")
                with c7:
                    remaining = stock_qty - qty_to_dispense
                    st.write(f"Remaining: {remaining}")
                dispense_plan.append({
                    "raw": med_text,
                    "display": display_name,
                    "generic": generic,
                    "brand": brand,
                    "stock_qty": stock_qty,
                    "dispense_qty": int(qty_to_dispense),
                    "matched_index": (matched.index[0] if (not matched.empty) else None)
                })

            if st.button("Confirm Dispensation for Selected Patient"):
                # Validate at least one positive dispense
                to_dispense = [d for d in dispense_plan if d["dispense_qty"] > 0]
                if not to_dispense:
                    st.warning("No dispense quantities greater than zero selected.")
                else:
                    # Update stock_df (in-memory) and persist
                    updated_stock = stock_df.copy()
                    dispensed_summary = []
                    for d in to_dispense:
                        qty = d["dispense_qty"]
                        if d["matched_index"] is not None:
                            idx = d["matched_index"]
                            # decrement
                            updated_stock.loc[updated_stock.index == idx, "StockQty"] = updated_stock.loc[updated_stock.index == idx, "StockQty"].astype(int) - qty
                            new_stock_val = int(updated_stock.loc[updated_stock.index == idx, "StockQty"].iloc[0])
                        else:
                            # no matching stock row in table: add a new row with zero-qty minus qty (we'll set to 0 - qty prevented)
                            # Instead of creating negatives, we disallow dispensing if not in stock (sensible pharmacy constraint)
                            st.error(f"Cannot dispense {d['display']}: no stock entry found.")
                            continue

                        dispensed_summary.append({
                            "Medicine": d["display"],
                            "Generic": d["generic"],
                            "Brand": d["brand"],
                            "QuantityDispensed": qty,
                            "RemainingStock": new_stock_val
                        })

                    # persist stock
                    save_stock(updated_stock)
                    # update patients file with Dispensed info
                    patients_df.loc[patients_df["Patient ID"] == selected_patient, "Dispensed"] = "Yes"
                    # build dispensed details string
                    dd = "; ".join([f"{s['Medicine']} => {s['QuantityDispensed']} (remaining {s['RemainingStock']})" for s in dispensed_summary])
                    patients_df.loc[patients_df["Patient ID"] == selected_patient, "Dispensed Details"] = dd
                    patients_df.to_csv(SAVE_FILE, index=False)

                    st.success("Dispensation recorded and stock updated.")
                    st.subheader("Dispensed summary")
                    st.table(pd.DataFrame(dispensed_summary))
                    # refresh in-memory stock
                    stock_df = load_stock()
    else:
        st.info("No patient records found. Save a patient record first in Patient Entry tab.")

