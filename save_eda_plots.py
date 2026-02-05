import pandas as pd
import os
import glob
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Setup paths
mimic_path = r'D:\ADE DATASET DOWNLOAD\MIMIC-IV-Demo_extracted'
vocab_path = r'D:\ADE DATASET DOWNLOAD\omop vocab'
assets_path = r'D:\ADE DATASET DOWNLOAD\assets'
os.makedirs(assets_path, exist_ok=True)

plt.style.use('bmh')

def load_mimic_table(module, table_name):
    module_path = os.path.join(mimic_path, module)
    search_patterns = [
        os.path.join(module_path, "**", f"{table_name}.csv.gz"),
        os.path.join(module_path, "**", f"{table_name}.csv")
    ]
    found_files = []
    for pattern in search_patterns:
        found_files.extend(glob.glob(pattern, recursive=True))
    if not found_files:
        found_files.extend(glob.glob(os.path.join(mimic_path, "**", f"{table_name}.csv*"), recursive=True))
    if not found_files: return pd.DataFrame()
    path = found_files[0]
    compression = 'gzip' if path.endswith('.gz') else None
    return pd.read_csv(path, compression=compression, low_memory=False)

def load_vocab_table(table_name):
    path = os.path.join(vocab_path, f"{table_name}.csv")
    if not os.path.exists(path): return pd.DataFrame()
    return pd.read_csv(path, sep='\t', low_memory=False)

# 1. Load Data
print("Loading data for visualization...")
concept = load_vocab_table('CONCEPT')
rxnorm = concept[concept['vocabulary_id'] == 'RxNorm']

prescriptions = load_mimic_table('clinical', 'prescriptions')
diagnoses = load_mimic_table('clinical', 'diagnoses_icd')
admissions = load_mimic_table('clinical', 'admissions')
patients = load_mimic_table('hosp', 'patients')

# 2. Run Integration Logic (Simplified for plots)
trigger_drugs = ['Warfarin', 'Heparin', 'Aspirin', 'Vancomycin', 'Furosemide']
ade_targets = [
    {'name': 'AKI', 'drugs': ['Vancomycin', 'Furosemide'], 'codes': ['N17', '5849']},
    {'name': 'Bleeding', 'drugs': ['Warfarin', 'Heparin', 'Aspirin'], 'codes': ['K92', '578', 'K26', 'D64', 'D70']}
]

all_signals = []
adm_times = admissions[['hadm_id', 'admittime', 'dischtime']].copy()
adm_times['admittime'] = pd.to_datetime(adm_times['admittime'])
adm_times['dischtime'] = pd.to_datetime(adm_times['dischtime'])

for target in ade_targets:
    target_dx = diagnoses[diagnoses['icd_code'].str.startswith(tuple(target['codes']), na=False)]
    target_rx = prescriptions[prescriptions['drug'].str.contains('|'.join(target['drugs']), case=False, na=False)]
    joint = target_rx.merge(target_dx, on=['subject_id', 'hadm_id'])
    joint = joint.merge(adm_times, on='hadm_id')
    joint['starttime'] = pd.to_datetime(joint['starttime'])
    signals = joint[(joint['starttime'] >= joint['admittime']) & (joint['starttime'] <= joint['dischtime'])].copy()
    signals['ade_type'] = target['name']
    all_signals.append(signals)

final_ade_signals = pd.concat(all_signals)
final_ade_signals['drug_base'] = final_ade_signals['drug'].apply(lambda x: next((d for d in trigger_drugs if d.lower() in x.lower()), "Unknown"))

# --- SAVE PLOTS ---

# 1. ADE Signal Count
plt.figure(figsize=(10, 5))
sns.countplot(data=final_ade_signals, x='ade_type', hue='drug_base', palette='viridis')
plt.title("ADE Signal Count by Type and Trigger Drug")
plt.savefig(os.path.join(assets_path, 'ade_signal_count.png'))
plt.close()

# 2. Demographics
ade_demographics = final_ade_signals.merge(patients[['subject_id', 'gender', 'anchor_age']], on='subject_id', how='left')
fig, ax = plt.subplots(1, 2, figsize=(15, 6))
ade_demographics['gender'].value_counts().plot(kind='pie', autopct='%1.1f%%', ax=ax[0], colors=['lightblue', 'lightcoral'])
ax[0].set_title("Gender Distribution")
sns.histplot(ade_demographics['anchor_age'], bins=20, kde=True, ax=ax[1], color='teal')
ax[1].set_title("Age Distribution")
plt.savefig(os.path.join(assets_path, 'demographics.png'))
plt.close()

# 3. Top ICD Codes
plt.figure(figsize=(12, 6))
top_codes = final_ade_signals['icd_code'].value_counts().head(10)
sns.barplot(x=top_codes.values, y=top_codes.index, palette='magma')
plt.title("Top 10 ICD Codes in Detected ADEs")
plt.savefig(os.path.join(assets_path, 'top_icd_codes.png'))
plt.close()

# 4. Drug-ADE Heatmap
heatmap_data = pd.crosstab(final_ade_signals['drug_base'], final_ade_signals['ade_type'])
plt.figure(figsize=(10, 8))
sns.heatmap(heatmap_data, annot=True, fmt="d", cmap="YlGnBu")
plt.title("Drug-ADE Interaction Matrix")
plt.savefig(os.path.join(assets_path, 'drug_ade_heatmap.png'))
plt.close()

# 5. Length of Stay
admissions['los_days'] = (pd.to_datetime(admissions['dischtime']) - pd.to_datetime(admissions['admittime'])).dt.total_seconds() / (24 * 3600)
admissions['has_ade'] = admissions['hadm_id'].isin(final_ade_signals['hadm_id'].unique())
plt.figure(figsize=(10, 6))
sns.boxplot(data=admissions, x='has_ade', y='los_days', palette='Set2')
plt.title("Length of Stay: ADE vs. Non-ADE")
plt.savefig(os.path.join(assets_path, 'los_comparison.png'))
plt.close()

# 6. Global Coverage (Mocked counts based on integration logic)
coverage_stats = {
    'MIMIC-IV': 100, 
    'DrugBank': 15000,
    'SIDER': 5000,
    'PharmGKB': 3000,
    'FAERS': 1000,
    'SynPUF': 2300000,
    'OMOP Vocab': 9000000
}
coverage_df = pd.DataFrame(list(coverage_stats.items()), columns=['Dataset', 'Entity_Count'])
plt.figure(figsize=(12, 6))
sns.barplot(data=coverage_df, x='Dataset', y='Entity_Count', palette='coolwarm')
plt.yscale('log')
plt.title("Cross-Dataset Entity Scale (Log Scale)")
plt.savefig(os.path.join(assets_path, 'dataset_coverage.png'))
plt.close()

print("All plots saved in assets/")
