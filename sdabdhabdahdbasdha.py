import pandas as pd
import streamlit as st
import os

# Load dataset
df = pd.read_csv(r"C:\\Users\\Administrator\\Downloads\\Drug_Audit_AI_completed_final.csv")
df.columns = df.columns.str.strip()

# File to save patient records
SAVE_FILE = "patient_records.csv"

# Body part to symptom keyword mapping (unchanged)
body_part_map = {
    "Head & Brain": [
        "headache", "dizziness", "migraine", "memory complaints", "concentration difficulties",
        "cognitive decline", "focal seizures", "seizure episodes", "loss of awareness",
        "psychosis symptoms", "delusions", "hallucinations", "disorganized behavior",
        "low mood", "anhedonia", "anxiety", "poor sleep", "sleep disturbance"
    ],
    "Eyes": [
        "eye pain", "ocular inflammation", "redness", "photophobia", "itchy eyes", "watery eyes",
        "foreign body sensation", "eye redness", "purulent discharge", "pain/irritation in eye"
    ],
    "Nose & Throat": [
        "sneezing", "rhinorrhea", "nasal congestion", "itchy/watery eyes", "urticaria",
        "pruritus", "allergic rhinitis"
    ],
    "Chest & Lungs": [
        "wheezing", "shortness of breath", "chest tightness", "cough", "bronchospasm",
        "productive cough", "chest congestion", "expectoration difficulty", "nocturnal cough"
    ],
    "Heart & Circulation": [
        "palpitations", "exercise intolerance", "heart failure symptoms", "hypertension symptoms",
        "elevated blood pressure"
    ],
    "Stomach & Digestive": [
        "heartburn", "acid regurgitation", "epigastric pain", "dyspepsia", "abdominal discomfort",
        "nausea", "vomiting", "early satiety", "abdominal cramps", "diarrhea",
        "acute watery diarrhea", "constipation", "hard stools", "incomplete evacuation"
    ],
    "Liver & Kidneys": [
        "hepatic encephalopathy", "confusion", "fatigue", "anorexia", "kidney dysfunction",
        "edema"
    ],
    "Muscles & Bones": [
        "spasticity", "muscle stiffness", "spasm-related pain", "bone pain", "muscle cramps",
        "joint pain", "musculoskeletal pain", "inflammation"
    ],
    "Blood & Metabolism": [
        "polyuria", "polydipsia", "polyphagia", "hyperglycemia", "anemia", "fatigue", "pallor",
        "dyspnea on exertion", "megaloblastic anemia", "nutritional deficiency", "poor appetite",
        "asymptomatic hyperlipidemia", "elevated cholesterol", "xanthomas"
    ],
    "Reproductive System": [
        "pelvic pain", "dysmenorrhea", "heavy menstrual bleeding", "ovarian dysfunction",
        "irregular menses", "infertility", "breast lump", "postpartum bleeding",
        "uterine cramping", "oral/vaginal itching", "white discharge"
    ],
    "Urinary System": [
        "dysuria", "urinary urgency", "urinary frequency", "urge incontinence", "nocturia"
    ],
    "General/Systemic": [
        "fever", "chills", "sweating", "myalgia", "infection signs", "sepsis",
        "localized pain", "acute pain", "moderate pain"
    ],
    "Nerves & Sensation": [
        "burning", "tingling", "neuropathic pain", "allodynia", "peripheral neuropathy"
    ]
}

# Collect all symptoms from dataset
symptom_cols = [
    "Core_Symptoms",
    "Core_Symptom_1", "Core_Symptom_2", "Core_Symptom_3", "Core_Symptom_4",
    "Core_Symptom_5", "Core_Symptom_6", "Core_Symptom_7", "Core_Symptom_8"
]

all_symptoms = pd.unique(df[symptom_cols].values.ravel())
all_symptoms = [s for s in all_symptoms if pd.notna(s)]

# Collect all medicines from dataset for dropdown
all_medicines = sorted(pd.unique(df["Generic_Name"].dropna().values))

# Initialize session state
if "diagnosis_results" not in st.session_state:
    st.session_state["diagnosis_results"] = None
if "grouped" not in st.session_state:
    st.session_state["grouped"] = {}
if "final_reps" not in st.session_state:
    st.session_state["final_reps"] = []

st.title("Medical Camp Diagnostic App")
st.write("Select gender, then body part, then choose up to 8 symptoms to see possible diagnoses and medicines with probabilities.")

# Tabs
tab1, tab2 = st.tabs(["Diagnosis & Treatment", "Patient Records"])

with tab1:
    # Patient info inputs
    st.header("Patient Information")
    patient_id = st.text_input("Patient ID")
    patient_name = st.text_input("Patient Name")
    patient_history = st.text_area("History")

    # Vitals
    st.subheader("Vitals")
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        bp_sys = st.number_input("BP Systolic", min_value=0, step=1, key="bp_sys")
    with col_v2:
        bp_dia = st.number_input("BP Diastolic", min_value=0, step=1, key="bp_dia")
    with col_v3:
        heart_rate = st.number_input("Heart Rate (BPM)", min_value=0, step=1, key="heart_rate")

    # Gender selection
    gender = st.selectbox("Select Gender", ["Male", "Female"])

    # Body part
    body_parts = list(body_part_map.keys())
    selected_part = st.selectbox("Select Body Part", body_parts)

    # Symptom selection
    st.subheader("Symptom Selection (Cross-System)")
    selected_symptoms = st.multiselect(
        "Select up to 8 Symptoms",
        options=sorted(all_symptoms),
        max_selections=8
    )

    # Button to compute diagnosis
    if st.button("Get Diagnosis"):
        if not selected_symptoms:
            st.warning("Please select at least one symptom.")
        else:
            results = []
            for _, row in df.iterrows():
                row_symptoms = [str(row[col]).lower() for col in symptom_cols if pd.notna(row[col])]
                matched = [sym for sym in selected_symptoms if any(sym.lower() in rs for rs in row_symptoms)]
                match_count = len(matched)
                if match_count > 0:
                    probability = round((match_count / len(selected_symptoms)) * 100, 2)
                    indications = [str(row[col]) for col in df.columns if "Indication" in col and pd.notna(row[col])]
                    medicine = row["Generic_Name"] if "Generic_Name" in df.columns else "N/A"
                    results.append({
                        "Probability (%)": probability,
                        "Matched Symptoms": matched,
                        "Indications": ", ".join(indications),
                        "Medicine": medicine
                    })

            if results:
                diagnosis_results = pd.DataFrame(results).sort_values(by="Probability (%)", ascending=False)
                st.session_state["diagnosis_results"] = diagnosis_results

                # Group by indication
                grouped = {}
                for r in results:
                    for ind in r["Indications"].split(", "):
                        if ind not in grouped:
                            grouped[ind] = {"Probability": r["Probability (%)"], "Medicines": set()}
                        grouped[ind]["Medicines"].add(r["Medicine"])
                st.session_state["grouped"] = grouped

                # Representative medicines
                all_meds_set = set()
                for details in grouped.values():
                    all_meds_set.update(details["Medicines"])
                st.session_state["final_reps"] = sorted(all_meds_set)

                st.success("Diagnosis computed. Scroll down to see recommendations & pick medicines.")

            else:
                st.error("No matching diagnoses found.")
                st.session_state["diagnosis_results"] = None
                st.session_state["grouped"] = {}
                st.session_state["final_reps"] = []

    # Show results
    diagnosis_results = st.session_state.get("diagnosis_results")
    grouped = st.session_state.get("grouped", {})
    final_reps = st.session_state.get("final_reps", [])

    if diagnosis_results is not None:
        col1, col2 = st.columns([1, 1.2])

        with col1:
            st.subheader("✅ Final Recommendations (Summary)")
            for ind, details in grouped.items():
                meds_list = sorted(details["Medicines"])
                final_med = meds_list[0] if meds_list else "N/A"
                st.caption(f"**{ind}** → {final_med}")

        with col2:
            st.subheader("📊 Grouped by Indication")
            for ind, details in grouped.items():
                with st.expander(f"{ind} — {details['Probability']}% match"):
                    st.write("Suggested Medicines:")
                    st.write(", ".join(sorted(details["Medicines"])))

        with st.expander("📋 Full Matching Results (Raw Table)"):
            st.dataframe(diagnosis_results)

        # Medicine selection
        st.header("Select Medicines Given to Patient")
        recommended_meds = sorted(set(final_reps))
        given_meds_recommended = st.multiselect(
            "Pick from recommended medicines",
            options=recommended_meds,
            default=recommended_meds
        )
        given_meds_other = st.multiselect(
            "Add other medicines from database (optional)",
            options=all_medicines
        )

        given_meds = []
        for m in given_meds_recommended + given_meds_other:
            if m and m not in given_meds:
                given_meds.append(m)

        if st.button("Save Patient Record"):
            if not patient_id or not patient_name:
                st.error("Please enter Patient ID and Patient Name.")
            elif not selected_symptoms:
                st.error("Please select symptoms before saving.")
            elif not given_meds:
                st.error("Please select at least one medicine.")
            else:
                record = {
                    "Patient ID": patient_id,
                    "Patient Name": patient_name,
                    "History": patient_history,
                    "BP": f"{bp_sys}/{bp_dia}",
                    "Heart Rate": heart_rate,
                    "Gender": gender,
                    "Body Part": selected_part,
                    "Selected Symptoms": "; ".join(selected_symptoms),
                    "Given Medicines": "; ".join(given_meds),
                }

                top5 = diagnosis_results.head(5)
                record["Top Diagnoses"] = "; ".join(
                    f"{row['Indications']} ({row['Probability (%)']}%)" for _, row in top5.iterrows()
                )

                if os.path.exists(SAVE_FILE):
                    saved_df = pd.read_csv(SAVE_FILE)
                    if patient_id in saved_df["Patient ID"].astype(str).values:
                        saved_df.loc[saved_df["Patient ID"].astype(str) == str(patient_id), list(record.keys())] = list(record.values())
                    else:
                        saved_df = pd.concat([saved_df, pd.DataFrame([record])], ignore_index=True)
                else:
                    saved_df = pd.DataFrame([record])

                saved_df.to_csv(SAVE_FILE, index=False)
                st.success("Patient record saved successfully!")
                st.subheader("Saved Patient Record")
                st.json(record)

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
                    st.rerun()

        st.subheader("All Patient Records")
        st.dataframe(edited_df)
    else:
        st.info("No patient records found. Save some records in the 'Diagnosis & Treatment' tab first.")
