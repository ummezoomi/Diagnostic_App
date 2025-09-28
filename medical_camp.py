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

# Initialize session state keys (so values persist across reruns)
if "diagnosis_results" not in st.session_state:
    st.session_state["diagnosis_results"] = None
if "results_list" not in st.session_state:
    st.session_state["results_list"] = None
if "grouped" not in st.session_state:
    st.session_state["grouped"] = {}
if "grouped_categories" not in st.session_state:
    st.session_state["grouped_categories"] = {}
if "final_reps" not in st.session_state:
    st.session_state["final_reps"] = []

st.title("Medical Camp Diagnostic App")
st.write("Select gender, then body part, then choose up to 8 symptoms to see possible diagnoses and medicines with probabilities.")

# Tabs for main app and patient records
tab1, tab2 = st.tabs(["Diagnosis & Treatment", "Patient Records"])

with tab1:
    # Patient info inputs
    st.header("Patient Information")
    patient_id = st.text_input("Patient ID")
    patient_name = st.text_input("Patient Name")
    patient_history = st.text_area("History")

    # Split vitals into BP + HR (structured)
    st.subheader("Vitals")
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        bp_sys = st.number_input("BP Systolic", min_value=0, step=1, key="bp_sys")
    with col_v2:
        bp_dia = st.number_input("BP Diastolic", min_value=0, step=1, key="bp_dia")
    with col_v3:
        heart_rate = st.number_input("Heart Rate (BPM)", min_value=0, step=1, key="heart_rate")

    # Step 1: Gender selection
    gender = st.selectbox("Select Gender", ["Male", "Female"])

    # Step 2: Body part selection
    body_parts = list(body_part_map.keys())
    selected_part = st.selectbox("Select Body Part", body_parts)

    # Step 3: Symptom selection (filtered by body part)
    relevant_keywords = body_part_map[selected_part]
    filtered_symptoms = [sym for sym in all_symptoms if any(k in str(sym).lower() for k in relevant_keywords)]

    selected_symptoms = st.multiselect(
        "Select up to 8 Symptoms",
        options=filtered_symptoms if filtered_symptoms else all_symptoms,
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
                match_count = sum(any(sel.lower() in rs for rs in row_symptoms) for sel in selected_symptoms)
                if match_count > 0:
                    probability = round((match_count / len(selected_symptoms)) * 100, 2)
                    indications = [str(row[col]) for col in df.columns if "Indication" in col and pd.notna(row[col])]
                    medicine = row["Generic_Name"] if "Generic_Name" in df.columns else "N/A"
                    results.append({
                        "Probability (%)": probability,
                        "Matched Symptoms": match_count,
                        "Indications": ", ".join(indications),
                        "Medicine": medicine
                    })

            if results:
                diagnosis_results = pd.DataFrame(results).sort_values(by="Probability (%)", ascending=False)
                # save to session_state so selections persist across reruns
                st.session_state["diagnosis_results"] = diagnosis_results
                st.session_state["results_list"] = results

                # --- Higher-level Grouping (same as before) ---
                category_map = {
                    "Post-operative ocular inflammation (e.g., after cataract surgery)": ["Post-operative ocular inflammation (e.g., after cataract surgery)"],
                    "Anterior uveitis (off-label)": ["Anterior uveitis (off-label)"],
                    "Allergic rhinitis": ["Allergic rhinitis"],
                    "Chronic spontaneous urticaria": ["Chronic spontaneous urticaria"],
                    "Spasticity due to multiple sclerosis": ["Spasticity due to multiple sclerosis"],
                    "Spinal cord injury-related spasticity": ["Spinal cord injury-related spasticity"],
                    "Asthma": ["Asthma"],
                    "Chronic obstructive pulmonary disease (COPD)": ["Chronic obstructive pulmonary disease (COPD)"],
                    "Gastroesophageal reflux disease (GERD)": ["Gastroesophageal reflux disease (GERD)"],
                    "Gastric ulcer": ["Gastric ulcer"],
                    "Duodenal ulcer": ["Duodenal ulcer"],
                    "Erosive esophagitis": ["Erosive esophagitis"],
                    "Cognitive support adjunct (limited evidence)": ["Cognitive support adjunct (limited evidence)"],
                    "Mild cognitive impairment (investigational/supplement use)": ["Mild cognitive impairment (investigational/supplement use)"],
                    "Focal (partial) seizures": ["Focal (partial) seizures"],
                    "Adjunctive therapy for epilepsy": ["Adjunctive therapy for epilepsy"],
                    "Osteoporosis prevention/treatment adjunct": ["Osteoporosis prevention/treatment adjunct"],
                    "Calcium/vitamin D deficiency": ["Calcium/vitamin D deficiency"],
                    "Type 2 diabetes mellitus": ["Type 2 diabetes mellitus"],
                    "Reduce risk of heart failure hospitalization (where indicated)": ["Reduce risk of heart failure hospitalization (where indicated)"],
                    "CKD adjunct therapy (where indicated)": ["CKD adjunct therapy (where indicated)"],
                    "Major depressive disorder": ["Major depressive disorder"],
                    "Generalized anxiety disorder (some agents)": ["Generalized anxiety disorder (some agents)"],
                    "Panic disorder/social anxiety (agent-dependent)": ["Panic disorder/social anxiety (agent-dependent)"],
                    "Osteoarthritis": ["Osteoarthritis"],
                    "Rheumatoid arthritis": ["Rheumatoid arthritis"],
                    "Acute musculoskeletal pain": ["Acute musculoskeletal pain"],
                    "Used when risk of NSAID-induced gastric ulcer exists (misoprostol provides gastroprotection)": ["Used when risk of NSAID-induced gastric ulcer exists (misoprostol provides gastroprotection)"],
                    "Uncomplicated malaria": ["Uncomplicated malaria"],
                    "Plasmodium falciparum infection": ["Plasmodium falciparum infection"],
                    "Malaria in chloroquine-resistant areas": ["Malaria in chloroquine-resistant areas"],
                    "Postoperative pain": ["Postoperative pain"],
                    "Musculoskeletal pain": ["Musculoskeletal pain"],
                    "Acute injury pain": ["Acute injury pain"],
                    "Urinary tract infections": ["Urinary tract infections"],
                    "Respiratory tract infections (some indications)": ["Respiratory tract infections (some indications)"],
                    "Skin/soft tissue infections": ["Skin/soft tissue infections"],
                    "Complicated intra-abdominal infections (moxifloxacin)": ["Complicated intra-abdominal infections (moxifloxacin)"],
                    "Endometriosis-associated pain": ["Endometriosis-associated pain"],
                    "Uterine fibroid-related heavy bleeding (some approvals)": ["Uterine fibroid-related heavy bleeding (some approvals)"],
                    "Supplementation for dietary insufficiency": ["Supplementation for dietary insufficiency"],
                    "Pregnancy (prenatal multivitamins, product-dependent)": ["Pregnancy (prenatal multivitamins, product-dependent)"],
                    "Hepatic encephalopathy (ammonia-lowering adjunct)": ["Hepatic encephalopathy (ammonia-lowering adjunct)"],
                    "Chronic liver disease support (adjunct)": ["Chronic liver disease support (adjunct)"],
                    "Hypertension": ["Hypertension"],
                    "Cardiovascular risk reduction (specific agents)": ["Cardiovascular risk reduction (specific agents)"],
                    "Chronic kidney disease associated with type 2 diabetes (to reduce renal and CV outcomes)": ["Chronic kidney disease associated with type 2 diabetes (to reduce renal and CV outcomes)"],
                    "Iron deficiency anemia": ["Iron deficiency anemia"],
                    "Pregnancy-related iron supplementation (when indicated)": ["Pregnancy-related iron supplementation (when indicated)"],
                    "Constipation": ["Constipation"],
                    "Irritable bowel syndrome with constipation (adjunct)": ["Irritable bowel syndrome with constipation (adjunct)"],
                    "Bacterial infection (agent-specific indications)": ["Bacterial infection (agent-specific indications)"],
                    "Heart rate control in some patients": ["Heart rate control in some patients"],
                    "First-line for T2DM alongside lifestyle measures": ["First-line for T2DM alongside lifestyle measures"],
                    "Dry eye syndrome (ophthalmic)": ["Dry eye syndrome (ophthalmic)"],
                    "Osteoarthritis (intra-articular formulation)": ["Osteoarthritis (intra-articular formulation)"],
                    "Cough and bronchial secretions (expectorant/syrup)": ["Cough and bronchial secretions (expectorant/syrup)"],
                    "Upper respiratory tract support (herbal)": ["Upper respiratory tract support (herbal)"],
                    "Schizophrenia (adult)": ["Schizophrenia (adult)"],
                    "Chronic stable angina (selected)": ["Chronic stable angina (selected)"],
                    "Heart failure with reduced ejection fraction (rate control)": ["Heart failure with reduced ejection fraction (rate control)"],
                    "Polycystic ovary syndrome (PCOS) adjunct": ["Polycystic ovary syndrome (PCOS) adjunct"],
                    "Oocyte quality support in fertility (adjunct)": ["Oocyte quality support in fertility (adjunct)"],
                    "Focal (partial) seizures (adjunct or monotherapy)": ["Focal (partial) seizures (adjunct or monotherapy)"],
                    "Epilepsy management": ["Epilepsy management"],
                    "Hormone receptor-positive breast cancer (adjuvant/metastatic)": ["Hormone receptor-positive breast cancer (adjuvant/metastatic)"],
                    "Ovulation induction for infertility (off-label/selected use)": ["Ovulation induction for infertility (off-label/selected use)"],
                    "Major depressive disorder (selected countries/approved)": ["Major depressive disorder (selected countries/approved)"],
                    "Neuropathic pain (peripheral neuropathy)": ["Neuropathic pain (peripheral neuropathy)"],
                    "Postherpetic neuralgia (where approved)": ["Postherpetic neuralgia (where approved)"],
                    "Prevention of NSAID-induced gastric ulcers (with NSAID)": ["Prevention of NSAID-induced gastric ulcers (with NSAID)"],
                    "Medical termination of pregnancy (with mifepristone)": ["Medical termination of pregnancy (with mifepristone)"],
                    "Postpartum hemorrhage (off-label/in some guidelines)": ["Postpartum hemorrhage (off-label/in some guidelines)"],
                    "Bowel preparation for colonoscopy": ["Bowel preparation for colonoscopy"],
                    "Constipation (osmotic laxative)": ["Constipation (osmotic laxative)"],
                    "Acute muscle spasm": ["Acute muscle spasm"],
                    "Musculoskeletal pain with spasm": ["Musculoskeletal pain with spasm"],
                    "Generalized anxiety disorder (short-term)": ["Generalized anxiety disorder (short-term)"],
                    "Panic disorder": ["Panic disorder"],
                    "Acute stress-related anxiety (short-term)": ["Acute stress-related anxiety (short-term)"],
                    "Giardiasis": ["Giardiasis"],
                    "Cryptosporidiosis": ["Cryptosporidiosis"],
                    "Other protozoal infections": ["Other protozoal infections"],
                    "Dyspepsia/functional dyspepsia": ["Dyspepsia/functional dyspepsia"],
                    "Gastroesophageal reflux symptoms (prokinetic)": ["Gastroesophageal reflux symptoms (prokinetic)"],
                    "Nausea and vomiting (selected)": ["Nausea and vomiting (selected)"],
                    "Chemotherapy-induced nausea and vomiting": ["Chemotherapy-induced nausea and vomiting"],
                    "Postoperative nausea and vomiting": ["Postoperative nausea and vomiting"],
                    "Radiation-induced nausea": ["Radiation-induced nausea"],
                    "Asthma (maintenance therapy)": ["Asthma (maintenance therapy)"],
                    "Allergic rhinitis (adjunct)": ["Allergic rhinitis (adjunct)"],
                    "Hypercholesterolemia": ["Hypercholesterolemia"],
                    "Primary/secondary prevention of cardiovascular disease": ["Primary/secondary prevention of cardiovascular disease"],
                    "Allergic conjunctivitis (ocular antihistamine)": ["Allergic conjunctivitis (ocular antihistamine)"],
                    "Ocular inflammation (steroid-responsive)": ["Ocular inflammation (steroid-responsive)"],
                    "Allergic conjunctivitis (steroid)": ["Allergic conjunctivitis (steroid)"],
                    "Folate deficiency": ["Folate deficiency"],
                    "Adjunct in depression for methylfolate deficiency (in some formulations)": ["Adjunct in depression for methylfolate deficiency (in some formulations)"],
                    "Pregnancy supplementation (where appropriate)": ["Pregnancy supplementation (where appropriate)"],
                    "Asthma (adjunct inhaler)": ["Asthma (adjunct inhaler)"],
                    "Neuropathic pain (diabetic neuropathy, postherpetic)": ["Neuropathic pain (diabetic neuropathy, postherpetic)"],
                    "Fibromyalgia": ["Fibromyalgia"],
                    "Adjunct in partial seizures (agent-dependent)": ["Adjunct in partial seizures (agent-dependent)"],
                    "Overactive bladder (detrusor overactivity)": ["Overactive bladder (detrusor overactivity)"],
                    "Candidiasis (vaginal, oral, esophageal)": ["Candidiasis (vaginal, oral, esophageal)"],
                    "Systemic fungal infections (select indications)": ["Systemic fungal infections (select indications)"],
                    "Severe/complicated infections": ["Severe/complicated infections"],
                    "Hospital-acquired pneumonia": ["Hospital-acquired pneumonia"],
                    "Intra-abdominal infections": ["Intra-abdominal infections"],
                    "Sepsis": ["Sepsis"],
                    "Bacterial conjunctivitis with inflammation": ["Bacterial conjunctivitis with inflammation"],
                    "Ocular inflammation with suspected bacterial component (ophthalmic preparations)": ["Ocular inflammation with suspected bacterial component (ophthalmic preparations)"],
                    "Type 2 diabetes mellitus (adjunct to diet/exercise)": ["Type 2 diabetes mellitus (adjunct to diet/exercise)"],
                    "Major depressive disorder (Depression with insomnia/appetite loss)": ["Major depressive disorder (Depression with insomnia/appetite loss)"],
                    "Hypercholesterolemia (Cardiovascular risk reduction)": ["Hypercholesterolemia (Cardiovascular risk reduction)"],
                    "Acute infectious diarrhea (symptomatic relief in children and adults)": ["Acute infectious diarrhea (symptomatic relief in children and adults)"]
                }


                grouped = {}
                for r in results:
                    for ind in r["Indications"].split(", "):
                        if ind not in grouped:
                            grouped[ind] = {"Probability": r["Probability (%)"], "Medicines": set()}
                        grouped[ind]["Medicines"].add(r["Medicine"])
                st.session_state["grouped"] = grouped

                grouped_categories = {}
                for ind, details in grouped.items():
                    found = False
                    for cat, keywords in category_map.items():
                        if any(k in ind.lower() for k in keywords):
                            if cat not in grouped_categories:
                                grouped_categories[cat] = {"Indications": set(), "Medicines": set()}
                            grouped_categories[cat]["Indications"].add(ind)
                            grouped_categories[cat]["Medicines"].update(details["Medicines"])
                            found = True
                            break
                    if not found:
                        grouped_categories[ind] = {"Indications": {ind}, "Medicines": details["Medicines"]}
                st.session_state["grouped_categories"] = grouped_categories

                # compute representative medicine for each category and store as defaults
                # Flatten all medicines across diagnoses and remove duplicates
                all_meds_set = set()
                for details in grouped_categories.values():
                    all_meds_set.update(details["Medicines"])

                # Keep sorted list if you want order
                final_reps = sorted(all_meds_set)
                st.session_state["final_reps"] = final_reps


                st.success("Diagnosis computed. Scroll down to see recommendations & pick medicines.")

            else:
                st.error("No matching diagnoses found. Please try different symptoms.")
                # clear any previous diagnosis in session_state
                st.session_state["diagnosis_results"] = None
                st.session_state["results_list"] = None
                st.session_state["grouped"] = {}
                st.session_state["grouped_categories"] = {}
                st.session_state["final_reps"] = []

    # Show results from session_state (so they persist across reruns)
    diagnosis_results = st.session_state.get("diagnosis_results")
    grouped = st.session_state.get("grouped", {})
    grouped_categories = st.session_state.get("grouped_categories", {})
    final_reps = st.session_state.get("final_reps", [])

    if diagnosis_results is not None:
        # --- Layout ---
        col1, col2 = st.columns([1, 1.2])

        with col1:
            st.subheader("✅ Final Recommendations (Summary)")
            # show compact summary with representative med per category
            for cat, details in grouped_categories.items():
                meds_list = sorted(details["Medicines"])
                final_med = meds_list[0] if meds_list else "N/A"


                if final_med != "N/A":
                    if st.button(final_med, key=f"badge_{cat}"):
                        if "badge_meds" not in st.session_state:
                            st.session_state["badge_meds"] = []
                        if final_med not in st.session_state["badge_meds"]:
                            st.session_state["badge_meds"].append(final_med)
                st.caption(f"**{cat}** → {final_med}")

        with col2:
            st.subheader("📊 Grouped by Indication")
            for ind, details in grouped.items():
                with st.expander(f"{ind} — {details['Probability']}% match"):
                    st.write("Suggested Medicines:")
                    st.write(", ".join(sorted(details["Medicines"])))

        # Raw dataframe at bottom (optional)
        with st.expander("📋 Full Matching Results (Raw Table)"):
            st.dataframe(diagnosis_results)

        # ---------------------------
        # Medicine selection (stable, pre-selected defaults)
        # ---------------------------
        st.header("Select Medicines Given to Patient")

        # recommended_meds pulled from diagnosis_results medicines
        recommended_meds = sorted(set(final_reps))

        # Pre-select the final_reps (only those that are in recommended_meds)
        badge_meds = st.session_state.get("badge_meds", [])
        preselect = [m for m in final_reps + badge_meds if m in recommended_meds]

        # Multiselect for recommended medicines (pre-selected)
        given_meds_recommended = st.multiselect(
            "Pick from recommended medicines (these are pre-selected)",
            options=recommended_meds,
            default=preselect
        )

        # Multiselect for other medicines from database (searchable, multiple allowed)
        given_meds_other = st.multiselect(
            "Add other medicines from database (optional)",
            options=all_medicines
        )

        # Combine selected medicines, keep order: recommended first then others, remove duplicates
        given_meds = []
        for m in given_meds_recommended + given_meds_other:
            if m and m not in given_meds:
                given_meds.append(m)

        # Save button (unchanged logic)
        if st.button("Save Patient Record"):
            if not patient_id or not patient_name:
                st.error("Please enter Patient ID and Patient Name before saving.")
            elif not selected_symptoms:
                st.error("Please select symptoms before saving.")
            elif not given_meds:
                st.error("Please select at least one medicine given before saving.")
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

                # Append to CSV (update if patient ID exists)
                if os.path.exists(SAVE_FILE):
                    saved_df = pd.read_csv(SAVE_FILE)
                    if patient_id in saved_df["Patient ID"].astype(str).values:
                        # update the row matching patient_id
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

        # Show records in editable dataframe
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


#streamlit run C:\Users\Administrator\Desktop\DIAGNOSTIC\check.py