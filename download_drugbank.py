import requests
import os
import zipfile
import io
import sys

# Credentials
USERNAME = "m.a.moontasir.abtahee@g.bracu.ac.bd"
PASSWORD = "GBSABOBTIPNZ1$e"
VERSION = "5-1-14"
VERSION_HYPHEN = VERSION.replace(".", "-")

# Base URL
BASE_URL = f"https://go.drugbank.com/releases/{VERSION_HYPHEN}/downloads"

# Datasets to download
# Name: Slug
DATASETS = {
    "drugbank_full_database.xml": "all-full-database",
    "structure_external_links.csv": "all-structure-links",
    "external_drug_links.csv": "all-drug-links",
    "target_drug_uniprot_links.csv": "target-all-uniprot-links",
    "enzyme_drug_uniprot_links.csv": "enzyme-all-uniprot-links"
}

OUTPUT_DIR = r"d:\ADE DATASET DOWNLOAD\drugbank"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def download_and_extract(filename, slug):
    url = f"{BASE_URL}/{slug}"
    print(f"Downloading {filename} from {url}...", flush=True)
    
    try:
        response = requests.get(url, auth=(USERNAME, PASSWORD), stream=True)
        response.raise_for_status()
        
        print(f"Response received. Content size: {response.headers.get('Content-Length', 'unknown')}", flush=True)
        
        # Download in chunks to show progress
        content = b""
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                content += chunk
                # Optional: print dots for progress
        
        print(f"Download complete. Size: {len(content)} bytes", flush=True)
        
        print(f"Extracting {filename}...", flush=True)
        try:
            z = zipfile.ZipFile(io.BytesIO(content))
            z.extractall(OUTPUT_DIR)
            print(f"Successfully extracted {filename} contents to {OUTPUT_DIR}", flush=True)
            for name in z.namelist():
                print(f" - Extracted: {name}", flush=True)
        except zipfile.BadZipFile:
            path = os.path.join(OUTPUT_DIR, filename)
            with open(path, 'wb') as f:
                f.write(content)
            print(f"Successfully downloaded {filename} (not a zip)", flush=True)
            
    except Exception as e:
        print(f"Error downloading {filename}: {e}", flush=True)

def main():
    for filename, slug in DATASETS.items():
        download_and_extract(filename, slug)

if __name__ == "__main__":
    main()
