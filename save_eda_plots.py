import pandas as pd
import os
import glob
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import io
import struct
import xml.etree.ElementTree as ET

# Attempt to import LZO for SynPUF
try:
    import lzo
except ImportError:
    lzo = None

# Setup paths
base_path = r'D:\ADE DATASET DOWNLOAD'
mimic_path = os.path.join(base_path, 'MIMIC-IV-Demo_extracted')
vocab_path = os.path.join(base_path, 'omop vocab')
synpuf_path = os.path.join(base_path, 'SynPUF2.3M')
faers_path = os.path.join(base_path, 'FAERS', 'FAERSdata')
sider_path = os.path.join(base_path, 'SIDER')
drugbank_path = os.path.join(base_path, 'drugbank')
pgkb_path = os.path.join(base_path, 'PharmaGKB_extracted')
images_path = os.path.join(base_path, 'EDA', 'images')
os.makedirs(images_path, exist_ok=True)

plt.style.use('bmh')
sns.set_palette('husl')

def save_fig(name):
    plt.savefig(os.path.join(images_path, name), bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Saved: {name}")

def load_synpuf_lzo(filename, max_blocks=100):
    if lzo is None: return pd.DataFrame()
    path = os.path.join(synpuf_path, filename)
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
            c_data = f.read(4)
            if not c_data: break
            c_size = struct.unpack('>I', c_data)[0]
            f.read(4)
            comp_data = f.read(c_size)
            if len(comp_data) < c_size: break
            if c_size < u_size:
                try:
                    decompressed = lzo.decompress(comp_data, False, u_size)
                    all_data += decompressed
                except: continue
            else:
                all_data += comp_data
        try:
            return pd.read_csv(io.BytesIO(all_data), sep=',', low_memory=False)
        except:
            return pd.DataFrame()

# --- 1. OMOP Plots ---
def gen_omop_plots():
    print("Generating OMOP plots...")
    concept_path = os.path.join(vocab_path, 'CONCEPT.csv')
    if os.path.exists(concept_path):
        concept = pd.read_csv(concept_path, sep='\t', low_memory=False)
        concept.columns = [c.lower() for c in concept.columns]
        
        # Concept Distribution 2x2
        fig, axes = plt.subplots(2, 2, figsize=(20, 14))
        if 'vocabulary_id' in concept.columns:
            vc = concept['vocabulary_id'].value_counts().head(20)
            sns.barplot(x=vc.values, y=vc.index, ax=axes[0,0], palette='viridis')
            axes[0,0].set_title('Top 20 Vocabularies')
        
        if 'domain_id' in concept.columns:
            dc = concept['domain_id'].value_counts().head(20)
            sns.barplot(x=dc.values, y=dc.index, ax=axes[0,1], palette='magma')
            axes[0,1].set_title('Top 20 Domains')
            
        if 'concept_class_id' in concept.columns:
            cc = concept['concept_class_id'].value_counts().head(20)
            sns.barplot(x=cc.values, y=cc.index, ax=axes[1,0], palette='crest')
            axes[1,0].set_title('Top 20 Concept Classes')
            
        if 'standard_concept' in concept.columns:
            std_concept = concept['standard_concept'].value_counts()
            axes[1,1].pie(std_concept.values, labels=std_concept.index, autopct='%1.1f%%', startangle=90)
            axes[1,1].set_title('Standard Concept Distribution')
        save_fig('omop_concept_dist.png')

# --- 2. SynPUF Plots ---
def gen_synpuf_plots():
    print("Generating SynPUF plots...")
    person = load_synpuf_lzo('person.5.2.csv.lzo', max_blocks=150)
    if not person.empty:
        person.columns = [c.lower() for c in person.columns]
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        if 'year_of_birth' in person.columns:
            person['age'] = 2026 - person['year_of_birth']
            sns.histplot(person['age'], bins=25, kde=True, ax=axes[0,0], color='skyblue')
        if 'gender_concept_id' in person.columns:
            gc = person['gender_concept_id'].map({8507: 'M', 8532: 'F'}).value_counts()
            axes[0,1].pie(gc.values, labels=gc.index, autopct='%1.1f%%')
        if 'race_concept_id' in person.columns:
            rc = person['race_concept_id'].map({8516: 'B', 8527: 'W'}).value_counts()
            sns.barplot(x=rc.values, y=rc.index, ax=axes[1,0])
        save_fig('synpuf_demographics.png')

# --- 3. FAERS Plots ---
def gen_faers_plots():
    print("Generating FAERS plots...")
    def load_faers(prefix):
        files = glob.glob(os.path.join(faers_path, f'{prefix}*.txt'))
        if files: 
            df = pd.read_csv(files[0], sep='$', low_memory=False, nrows=20000)
            df.columns = [c.lower() for c in df.columns]
            return df
        return pd.DataFrame()

    drug = load_faers('DRUG')
    reac = load_faers('REAC')
    if not drug.empty and not reac.empty:
        merged = pd.merge(drug[['primaryid', 'drugname']], reac[['primaryid', 'pt']], on='primaryid')
        top_d = merged['drugname'].value_counts().head(10).index
        top_r = merged['pt'].value_counts().head(10).index
        pivot = merged[merged['drugname'].isin(top_d) & merged['pt'].isin(top_r)].pivot_table(index='drugname', columns='pt', values='primaryid', aggfunc='count', fill_value=0)
        plt.figure(figsize=(12, 8))
        sns.heatmap(pivot, annot=True, fmt='d', cmap='YlOrRd')
        plt.title('FAERS Drug-Reaction Co-occurrence (Top 10)')
        save_fig('faers_heatmap.png')

# --- 4. PharmGKB Plots ---
def gen_pgkb_plots():
    print("Generating PharmGKB plots...")
    gene_path = os.path.join(pgkb_path, 'genes', 'genes.tsv')
    if os.path.exists(gene_path):
        genes = pd.read_csv(gene_path, sep='\t')
        if 'Is VIP' in genes.columns:
            plt.figure(figsize=(8, 8))
            vc = genes['Is VIP'].value_counts()
            plt.pie(vc.values, labels=vc.index, autopct='%1.1f%%')
            plt.title('VIP Gene Distribution')
            save_fig('pgkb_vip.png')

# --- 5. MIMIC Plots ---
def gen_mimic_plots():
    print("Generating MIMIC plots...")
    # Top DX
    dx_path = glob.glob(os.path.join(mimic_path, '**', 'diagnoses_icd.csv*'), recursive=True)
    if dx_path:
        compression = 'gzip' if dx_path[0].endswith('.gz') else None
        dx = pd.read_csv(dx_path[0], compression=compression, nrows=20000)
        dx.columns = [c.lower() for c in dx.columns]
        if 'icd_code' in dx.columns:
            plt.figure(figsize=(10, 6))
            top_dx = dx['icd_code'].value_counts().head(15)
            sns.barplot(x=top_dx.values, y=top_dx.index, palette='magma')
            plt.title('Top 15 MIMIC Diagnosis Codes')
            save_fig('mimic_top_dx.png')

if __name__ == "__main__":
    gen_omop_plots()
    gen_synpuf_plots()
    gen_faers_plots()
    gen_pgkb_plots()
    gen_mimic_plots()
    # Integration and others already saved usually, but running them ensures completeness
    print("\nMaster Visual Asset Generation Extended COMPLETE.")
