import streamlit as st
import pandas as pd
import mysql.connector
import json
import os
from datetime import datetime

# --- SAFE IMPORTS FROM MAIN APP ---
try:
    from medical_camp import get_connection
except ImportError:
    st.error("❌ Critical Error: Could not import 'medical_camp.py'. Ensure both files are in the same folder.")
    st.stop()

# --- IMAGE SETUP ---
IMAGE_FOLDER = "dental_images"
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

def save_image(uploaded_file, patient_id, tag):
    """Saves uploaded image to local disk and returns the filename."""
    if uploaded_file is None:
        return None

    # Create unique filename: P_101_PreOp_20240101_120000.jpg
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"P_{patient_id}_{tag}_{timestamp}.jpg"
    filepath = os.path.join(IMAGE_FOLDER, filename)

    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return filename

def run_dental_app():
    st.set_page_config(layout="wide", page_title="Dental Camp Module")
    st.title("🦷 Dental Camp Module")

    # --- TABS ---
    tab1, tab2 = st.tabs(["Dental Assessment", "View Records"])

    # ==========================================
    # TAB 1: DENTAL ASSESSMENT
    # ==========================================
    with tab1:
        st.subheader("New Dental Visit")

        conn = get_connection()
        patients_df = pd.read_sql("SELECT * FROM patients ORDER BY patient_id DESC", conn)
        conn.close()

        patient_list = [f"{row['patient_id']} - {row['patient_name']}" for index, row in patients_df.iterrows()]
        selected_patient = st.selectbox("Select Patient", [""] + patient_list)

        if selected_patient:
            pid = int(selected_patient.split(" - ")[0])
            p_data = patients_df[patients_df['patient_id'] == pid].iloc[0]

            c1, c2, c3 = st.columns(3)
            c1.info(f"Name: {p_data['patient_name']}")
            c2.info(f"Age: {p_data['age']}")
            c3.info(f"Gender: {p_data['gender']}")

            # --- 1. History ---
            st.markdown("### 1. History & Complaints")
            col_a, col_b = st.columns(2)
            pc = col_a.text_area("Presenting Complaint", key=f"pc_{pid}")
            hpc = col_b.text_area("History of Presenting Complaint", key=f"hpc_{pid}")

            st.markdown("---")

            # --- 2. Dental History ---
            st.markdown("### 2. Dental History")
            dh_cols = st.columns(5)
            la_exp = dh_cols[0].checkbox("LA Experience?", key=f"la_{pid}")
            scaling = dh_cols[1].checkbox("Scaling?", key=f"sc_{pid}")
            filling = dh_cols[2].checkbox("Filling/RCT?", key=f"fl_{pid}")
            extract = dh_cols[3].checkbox("Extraction?", key=f"ex_{pid}")
            prosthesis = dh_cols[4].checkbox("Prosthesis?", key=f"pr_{pid}")

            st.markdown("---")

            # --- 3. Habits & Brushing ---
            st.markdown("### 3. Habits & Brushing")
            h_cols = st.columns(6)
            habits = {
                "Smoking": h_cols[0].checkbox("Smoking", key=f"h_sm_{pid}"),
                "Gutkha": h_cols[1].checkbox("Gutkha", key=f"h_gu_{pid}"),
                "Naswar": h_cols[2].checkbox("Naswar", key=f"h_na_{pid}"),
                "Pan": h_cols[3].checkbox("Pan/Betel", key=f"h_pa_{pid}"),
                "Mauva": h_cols[4].checkbox("Mauva", key=f"h_ma_{pid}"),
                "Alcohol": h_cols[5].checkbox("Alcohol", key=f"h_al_{pid}")
            }

            b_cols = st.columns(3)
            brush_type = b_cols[0].selectbox("Brushing Type", ["Nil", "Finger", "Miswak", "Brush"], key=f"b_type_{pid}")
            brush_freq = b_cols[1].selectbox("Frequency", ["OD (Once)", "BD (Twice)", "TDS (Thrice)"], key=f"b_freq_{pid}")
            brush_time = b_cols[2].selectbox("Timing", ["Morning", "Night", "Both"], key=f"b_time_{pid}")

            st.markdown("---")

            # --- 4. Medical Alert ---
            st.markdown("### 4. Medical Alert")
            med_conditions = ["Diabetes", "Hypertension (BP)", "Heart Disease", "Asthma", "Hepatitis", "Bleeding Disorder", "Pregnancy", "Allergies"]
            selected_meds = st.multiselect("Select Positive Findings", med_conditions, key=f"meds_{pid}")

            st.markdown("---")

            # --- 5. Dentition Chart ---
            st.markdown("### 5. Dentition Status (Tooth Chart)")
            tooth_codes = ["Healthy", "Decayed (D)", "Filled (F)", "Mobile (M)", "BDR", "Missing"]

            st.write("**Upper Right (11-18)**")
            cols_ur = st.columns(8)
            ur_status = {str(t): cols_ur[i].selectbox(f"{t}", tooth_codes, key=f"t_{t}_{pid}", label_visibility="collapsed") for i, t in enumerate(range(18, 10, -1))}

            st.write("**Upper Left (21-28)**")
            cols_ul = st.columns(8)
            ul_status = {str(t): cols_ul[i].selectbox(f"{t}", tooth_codes, key=f"t_{t}_{pid}", label_visibility="collapsed") for i, t in enumerate(range(21, 29))}

            st.write("**Lower Left (31-38)**")
            cols_ll = st.columns(8)
            ll_status = {str(t): cols_ll[i].selectbox(f"{t}", tooth_codes, key=f"t_{t}_{pid}", label_visibility="collapsed") for i, t in enumerate(range(31, 39))}

            st.write("**Lower Right (48-41)**")
            cols_lr = st.columns(8)
            lr_status = {str(t): cols_lr[i].selectbox(f"{t}", tooth_codes, key=f"t_{t}_{pid}", label_visibility="collapsed") for i, t in enumerate(range(48, 40, -1))}

            st.markdown("---")

            # --- 6. Pictures (Pre/Post Op) ---
            st.markdown("### 6. Clinical Pictures")
            cam1, cam2 = st.columns(2)

            with cam1:
                st.write("**📸 Pre-Op Picture**")
                pre_img = st.camera_input("Take Pre-Op Photo", key=f"cam_pre_{pid}")

            with cam2:
                st.write("**📸 Post-Op Picture**")
                post_img = st.camera_input("Take Post-Op Photo", key=f"cam_post_{pid}")

            st.markdown("---")

            # --- 7. Diagnosis & Manual Rx ---
            st.markdown("### 7. Diagnosis & Manual Rx")
            prov_diag = st.text_input("Provisional Diagnosis", key=f"diag_{pid}")

            st.markdown("**Write Prescriptions**")
            med_list = []

            num_meds = st.number_input("Number of Medicines", 1, 10, 1, key=f"num_meds_{pid}")

            for i in range(num_meds):
                c1, c2 = st.columns([3, 2])
                m_name = c1.text_input(f"Medicine Name {i+1}", key=f"d_med_{i}_{pid}", placeholder="e.g. Amoxil 500mg")
                m_instr = c2.text_input(f"Dosage/Instr {i+1}", "1+0+1, 3 Days", key=f"d_ins_{i}_{pid}")

                if m_name:
                    med_list.append(f"{m_name} ({m_instr})")

            st.write("---")

            if st.button("💾 Save Dental Visit", type="primary", key=f"save_btn_{pid}"):
                # 1. Save Images
                pre_filename = save_image(pre_img, pid, "PreOp")
                post_filename = save_image(post_img, pid, "PostOp")

                # 2. Compile Data
                full_chart = {**ur_status, **ul_status, **ll_status, **lr_status}
                chart_data = {k: v for k, v in full_chart.items() if v != "Healthy"}
                chart_json = json.dumps(chart_data)
                meds_str = "; ".join(med_list)
                med_hist_str = ", ".join(selected_meds)

                conn = get_connection()
                cur = conn.cursor()

                sql = """
                    INSERT INTO dental_visits (
                        patient_id, doctor_name, visit_date, 
                        presenting_complaint, history_complaint,
                        la_experience, scaling, filling_rct, extraction, prosthesis,
                        smoking, gutkha, naswar, pan, mauva, alcohol,
                        brushing_type, brushing_freq, brushing_timing,
                        medical_history_notes, dentition_status,
                        provisional_diagnosis, medicines, dispensed,
                        pre_op_image, post_op_image
                    ) VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'No', %s, %s)
                """

                def yn(val): return 'Yes' if val else 'No'

                vals = (
                    pid, "Dentist",
                    pc, hpc,
                    yn(la_exp), yn(scaling), yn(filling), yn(extract), yn(prosthesis),
                    yn(habits['Smoking']), yn(habits['Gutkha']), yn(habits['Naswar']),
                    yn(habits['Pan']), yn(habits['Mauva']), yn(habits['Alcohol']),
                    brush_type, brush_freq, brush_time,
                    med_hist_str, chart_json,
                    prov_diag, meds_str,
                    pre_filename, post_filename
                )

                try:
                    cur.execute(sql, vals)
                    conn.commit()
                    st.success("✅ Dental Visit & Images Saved Successfully!")
                except Exception as e:
                    st.error(f"Error saving: {e}")
                finally:
                    conn.close()

    # ==========================================
    # TAB 2: RECORDS
    # ==========================================
    with tab2:
        st.header("Dental Records")

        col1, col2 = st.columns([1, 3])
        if col1.button("🔄 Refresh List"):
            st.rerun()

        conn = get_connection()

        # 1. Summary Table
        summary_df = pd.read_sql("""
            SELECT d.visit_id, p.patient_name, p.age, p.gender, d.visit_date, d.provisional_diagnosis
            FROM dental_visits d
            JOIN patients p ON d.patient_id = p.patient_id
            ORDER BY d.visit_date DESC
        """, conn)

        st.dataframe(summary_df, use_container_width=True)

        # 2. EXPORT BUTTON
        st.write("---")
        full_df = pd.read_sql("""
            SELECT *
            FROM dental_visits d
            JOIN patients p ON d.patient_id = p.patient_id
            ORDER BY d.visit_date DESC
        """, conn)

        csv = full_df.to_csv(index=False).encode('utf-8')
        col2.download_button(
            label="📥 Download Complete Records (Excel/CSV)",
            data=csv,
            file_name='dental_camp_full_data.csv',
            mime='text/csv',
        )

        st.write("---")
        st.subheader("🔍 View Full Case Detail")

        visit_ids = summary_df['visit_id'].tolist()
        selected_visit_id = st.selectbox("Select Visit ID to view details", [""] + [str(v) for v in visit_ids])

        if selected_visit_id:
            detail_df = pd.read_sql(f"SELECT * FROM dental_visits WHERE visit_id = {selected_visit_id}", conn)

            if not detail_df.empty:
                row = detail_df.iloc[0]

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### Clinical Info")
                    st.info(f"**PC:** {row['presenting_complaint']}\n\n**History:** {row['history_complaint']}")
                    st.warning(f"**Medical Alert:** {row['medical_history_notes']}")

                    st.markdown("#### Clinical Images")
                    i1, i2 = st.columns(2)

                    if row['pre_op_image']:
                        i1.image(os.path.join(IMAGE_FOLDER, row['pre_op_image']), caption="Pre-Op")
                    else:
                        i1.write("No Pre-Op Image")

                    if row['post_op_image']:
                        i2.image(os.path.join(IMAGE_FOLDER, row['post_op_image']), caption="Post-Op")
                    else:
                        i2.write("No Post-Op Image")

                with c2:
                    st.markdown("#### Habits & Findings")
                    habits_found = []
                    for h in ['smoking', 'gutkha', 'naswar', 'pan', 'mauva', 'alcohol']:
                        if row.get(h) == 'Yes': habits_found.append(h.capitalize())
                    st.write("**Habits:** " + (", ".join(habits_found) if habits_found else "None"))
                    st.write(f"**Brushing:** {row['brushing_type']} ({row['brushing_freq']})")

                    st.markdown("#### 🦷 Dentition")
                    try:
                        teeth_data = json.loads(row['dentition_status'])
                        if not teeth_data:
                            st.write("No issues recorded.")
                        else:
                            t_cols = st.columns(3)
                            for i, (tooth, status) in enumerate(teeth_data.items()):
                                t_cols[i % 3].error(f"**#{tooth}**: {status}")
                    except:
                        st.write("Error reading chart.")

                st.markdown("---")
                st.success(f"**Diagnosis:** {row['provisional_diagnosis']}")
                st.write(f"**Prescription:** {row['medicines']}")

        conn.close()

if __name__ == "__main__":
    run_dental_app()