# Adverse Drug Event (ADE) Detection & Integration Hub

A state-of-the-art research pipeline for identifying Adverse Drug Events (ADEs) by integrating 7 heterogeneous medical, pharmacological, and genomic datasets using the **OMOP Common Data Model (CDM)**.

---

## 🚀 Project Overview

This project implements a multi-source data integration framework designed to bridge the gap between real-world clinical evidence (MIMIC-IV), public safety reporting (FAERS), curated pharmacological knowledge (DrugBank, SIDER), and pharmacogenomics (PharmGKB).

### Core Capabilities

- **High-Fidelity Acquisition**: Automated daily-ready scripts for 7 massive datasets.
- **Identity Resolution**: Standardizing chemical and clinical nomenclature to the **OMOP CONCEPT** spine (RxNorm, SNOMED CT).
- **Temporal ADE Discovery**: A logic-based engine that identifies Adverse Drug Events in electronic health records by joining temporal medication starts with incident diagnosis codes.
- **Clinical Impact Quantification**: Statistical analysis of ADE burden, specifically measuring **hospital LOS (Length of Stay)** and admission severity.

---

## 🛠️ Repository Architecture

```text
.
├── EDA/                        # Exploratory Data Analysis Focus
│   ├── images/                 # Visual documentation assets
│   ├── 01_omop_vocab_eda.ipynb # Vocabulary mapping & concept hierarchies
│   ├── 02_synpuf_eda.ipynb     # Population-scale claims analysis (2.3M patients)
│   ├── 03_faers_eda.ipynb      # FDA Safety reporting trends (2019-2024)
│   ├── 04_sider_eda.ipynb      # ADR prevalence & Label complexity analysis
│   ├── 05_drugbank_eda.ipynb   # Polypharmacology & Chemical target mappings
│   ├── 06_pharmgkb_eda.ipynb   # Genomic susceptibility & VIP annotations
│   ├── 07_mimic_iv_demo_eda.ipynb # Intensive Care EHR profiling
│   └── 08_cross_dataset_integration_eda.ipynb  <-- MASTER RESEARCH HUB
├── download_*.py               # Robust acquisition scripts (LZO/GZ support)
├── main.py                     # Pipeline orchestration entry point
└── requirements.txt            # Data science dependency stack
```

---

## 📂 Deep Dataset Catalog & EDA Insights

### 1. MIMIC-IV Demo (Clinical Ground Truth)

- **Scope**: EHR data from Beth Israel Deaconess Medical Center.
- **Visual Evidence**:
  - ![MIMIC Admission Types](./EDA/images/mimic_dist.png)
    - *Explanation*: Shows the distribution of admission types (Emergency, Urgent, Elective), highlighting the high prevalence of acute cases which form the basis for ADE discovery.
  - ![Top ICD Codes](./EDA/images/mimic_top_dx.png)
    - *Explanation*: Identifies the most frequent diagnosis codes in the cohort, critical for filtering patient populations for specific ADE signals (e.g., AKI).
- **Key Finding**: ADE cases exhibit a **2x increase in Length of Stay** (median 11.6 days vs 5.6 days).

### 2. FAERS (Real-World Safety Signals)

- **Scope**: FDA Adverse Event Reporting System (2019-2024).
- **Visual Evidence**:
  - ![FAERS Reactions](./EDA/images/faers_reac.png)
    - *Explanation*: A frequency profile of the top 20 reported adverse reactions (PT levels), showing common outcomes like "Pyrexia" and "Pneumonia".
  - ![FAERS Heatmap](./EDA/images/faers_heatmap.png)
    - *Explanation*: A co-occurrence matrix between top drugs and reactions, revealing statistically significant clusters of safety reports.
- **Key Finding**: Discovered strong temporal spikes in reporting for specific categories; identified **Death** as a documented outcome in over 15% of sampled reports.

### 3. SIDER (Curated Side Effects)

- **Scope**: Side Effect Resource (ADR mapping to MedDRA).
- **Visual Evidence**:
  - ![SIDER Prevalence](./EDA/images/sider_prevalence.png)
    - *Explanation*: Visualizes the prevalence of documented side effects across the entire drug library, used as a reference to validate "expected" vs "unexpected" signals.
- **Key Finding**: Top prevalent side effects across all marketed drugs: **Dizziness, Nausea, and Headaches**.

### 4. DrugBank (Chemical Knowledge)

- **Scope**: Comprehensive drug-target database.
- **Visual Evidence**:
  - ![DrugBank Coverage](./EDA/images/drugbank_dist.png)
    - *Explanation*: Assesses the coverage of external identifiers (UniProt, CAS, ChEMBL) for the drug library, ensuring high connectivity for mapping to the OMOP vocabulary.
- **Key Finding**: Identified high **DDIs (Drug-Drug Interactions)** in biotech drugs vs. small molecules.

### 5. PharmGKB (Pharmacogenomics)

- **Scope**: Curated genomic susceptibility data.
- **Visual Evidence**:
  - ![PGKB VIP](./EDA/images/pgkb_vip.png)
    - *Explanation*: Distribution of "Very Important Pharmacogenes" (VIPs), which are prioritized in the pipeline for identifying genetic susceptibility to the ADEs found in MIMIC.

### 6. OMOP Vocabulary & SynPUF

- **Scope**: Standardized medical standard (CONCEPT) & 2.3M Claims.
- **Visual Evidence**:
  - ![OMOP Concept Dist](./EDA/images/omop_concept_dist.png)
    - *Explanation*: Breakdown of concepts by vocabulary (RxNorm, SNOMED) and domain, defining the mapping spine of the entire project.
  - ![SynPUF Demographics](./EDA/images/synpuf_demographics.png)
    - *Explanation*: Age and gender profiling of the SynPUF population, used to verify the synthetic dataset's representativeness of the US Medicare population.
  - ![SynPUF Visits](./EDA/images/synpuf_visits.png)
    - *Explanation*: Distribution of medical encounters (Inpatient vs Outpatient) within the claims data.

---

## 🔗 Master Integration: The ADE Discovery Hub

The final research stage (Notebook `08`) implements the **Cross-Dataset Integration Pipeline**:

### 1. Join Strategy & Identity Resolution

The pipeline uses the **OMOP CONCEPT** table as a "Rosetta Stone":

1. **Drug Resolution**: MIMIC prescription strings → RxNorm Concept IDs.
  - ![Top Mapped Drugs](./EDA/images/master_top_mapped.png)
    - *Explanation*: Showcases the highest-frequency drugs successfully mapped from source strings to RxNorm identifiers, demonstrating the robustness of the identity resolution phase.
1. **Signal Filter**: Hospital-acquired events (Diagnosis `starttime` BETWEEN Admission/Discharge).
2. **Validation**: Identified clinical signals are cross-referenced with **SIDER** and **PharmGKB**.

### 2. Research Findings & Visuals

- **Identified Signals**: **446 ADE Instances** (focused on AKI and Bleeding).
- ![ADE Signals](./EDA/images/master_ade_signals.png)
  - *Explanation*: Comparative breakdown of the two primary ADE types (AKI and Bleeding) identified through temporal clinical logic.
- ![Trigger Distribution](./EDA/images/master_trigger_dist.png)
  - *Explanation*: A deep dive into the specific drugs triggering each ADE type. For instance, show the relative contribution of Vancomycin vs Furosemide to AKI signals.
- ![LOS Impact](./EDA/images/master_los_impact.png)
  - *Explanation*: Demonstrates the massive clinical burden of ADEs, showing a multi-day increase in median Length of Stay for affected patients.
- ![Overall Coverage](./EDA/images/dataset_coverage.png)
  - *Explanation*: A summary of mapping efficiency across all 7 sources, showing the project's success in harmonizing disparate identifiers into a unified OMOP framework.

---

## ⚙️ Setup & Execution

1. **Virtual Environment**: `python -m venv venv`
2. **Dependencies**: `pip install -r requirements.txt`
3. **Data Generation**: Run individual `download_*.py` for specific sources.
4. **Analysis Hub**: Open `EDA/08_cross_dataset_integration_eda.ipynb` to execute the master mapping logic.

---
**Author**: Moontasir Abtahee  
**Vision**: Bridging chemical knowledge with clinical evidence through standardized CDM integration.
