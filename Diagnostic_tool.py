import pandas as pd

# Load both files
phase1 = pd.read_excel("ICD10_Symptom_Expanded_10000.xlsx")
phase2 = pd.read_excel("ICD10_Symptom_List_Phase2.xlsx")

# Keep only needed columns and make sure names match
phase1 = phase1.rename(columns={"Symptom_Name": "Symptom"})
phase1 = phase1[["Symptom", "Body_System"]]
phase2 = phase2[["Symptom", "Body_System"]]

# Combine and remove duplicates
merged = pd.concat([phase1, phase2], ignore_index=True)
merged = merged.drop_duplicates(subset=["Symptom"])

# Save to a new Excel file
merged.to_excel("ICD10_Symptom_List_All.xlsx", index=False)

print("Merged file created successfully!")