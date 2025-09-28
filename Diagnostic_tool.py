import pandas as pd

# Load dataset
# df = pd.read_csv(r"C:\Users\Administrator\Desktop\icd_diagnosis.csv")

# Define specialty keyword mapping
# specialties = {
#     "Dermatology": ["skin", "rash", "dermatitis", "eczema", "psoriasis", "acne", "burn", "ulcer", "cellulitis", "fungal", "alopecia"],
#     "Orthopedics": ["fracture", "dislocation", "arthritis", "joint", "sprain", "bone", "scoliosis", "spine", "musculoskeletal"],
#     "Cardiology": ["heart", "cardiac", "coronary", "angina", "arrhythmia", "myocarditis", "pericarditis", "hypertension", "heart failure"],
#     "Gastroenterology": ["stomach", "intestine", "colon", "liver", "gallbladder", "pancreas", "gastritis", "ulcer", "hepatitis", "cirrhosis", "bowel"],
#     "Neurology": ["brain", "nerve", "seizure", "epilepsy", "stroke", "migraine", "neuropathy", "multiple sclerosis", "parkinson", "dementia"],
#     "ENT": ["ear", "nose", "throat", "sinusitis", "otitis", "rhinitis", "pharyngitis", "tonsillitis", "laryngitis", "vertigo"],
#     "Gynecology": ["uterus", "cervix", "ovary", "endometriosis", "menstruation", "pregnancy", "pelvic", "breast"]
# }

# # Create a specialty column initialized as None
# df["Specialty"] = None
#
# # Assign specialty based on keyword matching
# for spec, keywords in specialties.items():
#     pattern = "|".join([f"\\b{kw}\\b" for kw in keywords])  # match whole words
#     mask = df["Diagnosis"].str.lower().str.contains(pattern, na=False)
#     df.loc[mask, "Specialty"] = spec
#
# # Save filtered dataset
# filtered_df = df[df["Specialty"].notna()]
# filtered_df.to_csv("filtered_specialties.csv", index=False)

#-------------------------------- FILTERING INTO 7 OTHER CSVS -----------------------
df = pd.read_csv("filtered_specialties.csv")

# Ensure 'Specialty' column exists
if "Specialty" not in df.columns:
    raise ValueError("Your CSV must have a 'Specialty' column for this to work")

# List of your chosen specialties
specialties = ["Dermatology", "Orthopedics", "Cardiology", "Gastroenterology", "Neurology", "ENT", "Gynecology"]

# Split and save each specialty into its own CSV
for spec in specialties:
    spec_df = df[df["Specialty"] == spec]
    spec_df.to_csv(f"{spec.lower()}_diagnoses.csv", index=False)

print("✅ Split complete! 7 CSV files created.")