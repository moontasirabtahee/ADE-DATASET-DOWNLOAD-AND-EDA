import pandas as pd
import os
import glob
import matplotlib.pyplot as plt
import numpy as np
import io
import struct

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
    try:
        return pd.read_csv(path, compression=compression, low_memory=False)
    except: return pd.DataFrame()

def load_vocab_table(table_name):
    path = os.path.join(vocab_path, f"{table_name}.csv")
    if not os.path.exists(path): return pd.DataFrame()
    try:
        return pd.read_csv(path, sep='\t', low_memory=False)
    except: return pd.DataFrame()

def load_synpuf_lzo(filename, max_blocks=100):
    try:
        import lzo
    except ImportError: return pd.DataFrame()
    path = os.path.join(r'D:\ADE DATASET DOWNLOAD\SynPUF2.3M', filename)
    if not os.path.exists(path): return pd.DataFrame()
    with open(path, 'rb') as f:
        content = f.read(1000)
        idx = content.find(b'\x00\x04\x00\x00')
        if idx == -1: 
            idx = content.find(b'\x00\x01\x00\x00')
            if idx == -1: return pd.DataFrame()
        f.seek(idx)
        all_data = b''
        for _ in range(max_blocks):
            u_data = f.read(4)
            if not u_data: break
            u_size = struct.unpack('>I', u_data)[0]
            if u_size == 0 or u_size > 1000000: break
            c_data = f.read(4); c_size = struct.unpack('>I', c_data)[0]
            f.read(4); comp_data = f.read(c_size)
            if c_size < u_size:
                try: all_data += lzo.decompress(comp_data, False, u_size)
                except: continue
            else: all_data += comp_data
        try:
            df = pd.read_csv(io.BytesIO(all_data), sep=',', low_memory=False)
            # DEDUPLICATE COLUMNS TO AVOID REINDEX ERROR
            df = df.loc[:, ~df.columns.duplicated()]
            return df
        except: return pd.DataFrame()

# 1. Load Core Data
print("Loading core data...")
concept = load_vocab_table('CONCEPT')
rxnorm = concept[concept['vocabulary_id'] == 'RxNorm'] if not concept.empty else pd.DataFrame()
prescriptions = load_mimic_table('clinical', 'prescriptions')
diagnoses = load_mimic_table('clinical', 'diagnoses_icd')
admissions = load_mimic_table('clinical', 'admissions')

def save_plot(name):
    plt.tight_layout()
    plt.savefig(os.path.join(assets_path, name))
    plt.close()
    print(f"  Saved {name}")

# --- GLOBAL PLOTS ---
print("Global Plots...")

# ADE Summary
if not admissions.empty and not prescriptions.empty and not diagnoses.empty:
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
        t_dx = diagnoses[diagnoses['icd_code'].str.startswith(tuple(target['codes']), na=False)]
        t_rx = prescriptions[prescriptions['drug'].str.contains('|'.join(target['drugs']), case=False, na=False)]
        joint = t_rx.merge(t_dx, on=['subject_id', 'hadm_id']).merge(adm_times, on='hadm_id')
        joint['starttime'] = pd.to_datetime(joint['starttime'])
        signals = joint[(joint['starttime'] >= joint['admittime']) & (joint['starttime'] <= joint['dischtime'])].copy()
        signals['ade_type'] = target['name']
        all_signals.append(signals)
    if all_signals:
        signals_df = pd.concat(all_signals)
        plt.figure(figsize=(10, 6))
        counts = signals_df['ade_type'].value_counts().to_dict()
        plt.bar(list(counts.keys()), list(counts.values()), color=['skyblue', 'salmon'])
        plt.title("Detected ADE Signals in MIMIC-IV")
        save_plot('ade_summary.png')

# --- DATASET SPECIFIC ---

# 1. OMOP
if not concept.empty:
    counts = concept['domain_id'].value_counts().head(10).to_dict()
    plt.figure(figsize=(10, 6))
    plt.barh(list(counts.keys()), list(counts.values()), color='teal')
    plt.gca().invert_yaxis()
    plt.title("OMOP Domain Distribution")
    save_plot('omop_dist.png')

# 2. SynPUF
p_df = load_synpuf_lzo('person.5.2.csv.lzo', max_blocks=100)
if not p_df.empty and 'year_of_birth' in p_df.columns:
    plt.figure(figsize=(10, 6))
    plt.hist(p_df['year_of_birth'].dropna(), bins=30, color='orange', edgecolor='black')
    plt.title("SynPUF: Birth Year Distribution")
    save_plot('synpuf_dist.png')

# 3. FAERS
f_path = glob.glob(os.path.join(r'D:\ADE DATASET DOWNLOAD\FAERS\FAERSdata', 'REAC*.txt'))
if f_path:
    try:
        r_df = pd.read_csv(f_path[0], sep='$', nrows=10000)
        counts = r_df['pt'].value_counts().head(10).to_dict()
        plt.figure(figsize=(12, 6))
        plt.barh([str(k)[:30] for k in counts.keys()], list(counts.values()), color='darkred')
        plt.gca().invert_yaxis()
        plt.title("FAERS: Top 10 Reactions")
        save_plot('faers_dist.png')
    except: pass

# 4. SIDER
s_path = r'D:\ADE DATASET DOWNLOAD\SIDER\meddra_all_se.tsv.gz'
if os.path.exists(s_path):
    try:
        s_se = pd.read_csv(s_path, sep='\t', names=['cid_a', 'cid_b', 'meddra_id', 'se_type', 'se_name'], compression='gzip')
        counts = s_se['se_name'].value_counts().head(10).to_dict()
        plt.figure(figsize=(12, 6))
        plt.barh([str(k)[:30] for k in counts.keys()], list(counts.values()), color='navy')
        plt.gca().invert_yaxis()
        plt.title("SIDER: Top 10 Side Effects")
        save_plot('sider_dist.png')
    except: pass

# 5. DrugBank
db_path = r'D:\ADE DATASET DOWNLOAD\drugbank\drug links.csv'
if os.path.exists(db_path) and not rxnorm.empty:
    try:
        links = pd.read_csv(db_path)
        cov = links.merge(rxnorm[['concept_name']].drop_duplicates(), left_on='Name', right_on='concept_name', how='inner')
        plt.figure(figsize=(8, 6))
        plt.bar(['DrugBank Total', 'RxNorm Mapped'], [len(links), len(cov)], color=['gray', 'blue'])
        plt.title("DrugBank to RxNorm Mapping")
        save_plot('drugbank_dist.png')
    except: pass

# 6. PharmGKB
pg_path = r'D:\ADE DATASET DOWNLOAD\PharmaGKB_extracted\drugs\drugs.tsv'
if os.path.exists(pg_path):
    try:
        pg_df = pd.read_csv(pg_path, sep='\t')
        if 'Is VIP' in pg_df.columns:
            plt.figure(figsize=(10, 6))
            pg_df['Is VIP'].value_counts().plot(kind='bar', color='salmon')
            plt.title("PharmGKB: VIP Status Distribution")
            save_plot('pharmgkb_dist.png')
    except: pass

# 7. MIMIC
if not admissions.empty:
    counts = admissions['admission_type'].value_counts().to_dict()
    plt.figure(figsize=(10, 6))
    plt.barh(list(counts.keys()), list(counts.values()), color='purple')
    plt.gca().invert_yaxis()
    plt.title("MIMIC-IV Admission Types")
    save_plot('mimic_dist.png')

print("Generating overall coverage matrix...")
try:
    coverage = {'MIMIC': 100, 'DrugBank': 15000, 'SIDER': 5000, 'FAERS': 1000000, 'PharmGKB': 3000, 'SynPUF': 2300000, 'OMOP': 9000000}
    plt.figure(figsize=(12, 6))
    plt.bar(list(coverage.keys()), list(coverage.values()), color='green')
    plt.yscale('log')
    plt.title("Data Entity Scale (Log Scale)")
    save_plot('overall_coverage.png')
except: pass

print("Done.")
