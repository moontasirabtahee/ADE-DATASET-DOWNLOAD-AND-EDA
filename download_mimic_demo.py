import os
import time
import requests
import logging
from typing import List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mimic_demo_download.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
OUTPUT_BASE = "MIMIC-IV-Demo"
RATE_LIMIT_DELAY = 1.0  # 1 request/second
MAX_RETRIES = 3

DATASETS = [
    {
        "name": "clinical",
        "slug": "mimic-iv-demo",
        "requested_v": "2.2",
        "fallback_vs": ["2.2", "1.0"],
        "purpose": "Core clinical data"
    },
    {
        "name": "ed",
        "slug": "mimic-iv-ed-demo",
        "requested_v": "2.2",
        "fallback_vs": ["2.2", "1.0"],
        "purpose": "Emergency department data"
    },
    {
        "name": "ecg",
        "slug": "mimic-iv-ecg-demo",
        "requested_v": "1.0",
        "fallback_vs": ["1.0", "0.1"],
        "purpose": "Diagnostic ECG waveforms"
    },
    {
        "name": "fhir",
        "slug": "mimic-iv-fhir-demo",
        "requested_v": "2.2",
        "fallback_vs": ["2.1.0", "2.0", "1.0"],
        "purpose": "FHIR R4 format"
    },
    {
        "name": "omop",
        "slug": "mimic-iv-demo-omop",
        "requested_v": "0.9",
        "fallback_vs": ["0.9"],
        "purpose": "OMOP Common Data Model format"
    },
    {
        "name": "meds",
        "slug": "mimic-iv-meds-demo",
        "requested_v": "0.0.1",
        "fallback_vs": ["0.0.1"],
        "purpose": "Medical Event Data Standard format"
    }
]

def download_physionet_dataset(dataset: Dict) -> bool:
    slug = dataset["slug"]
    name = dataset["name"]
    version_to_try = [dataset["requested_v"]] + [v for v in dataset["fallback_vs"] if v != dataset["requested_v"]]
    
    target_dir = os.path.join(OUTPUT_BASE, name)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    for version in version_to_try:
        url = f"https://physionet.org/content/{slug}/get-zip/{version}/"
        target_path = os.path.join(target_dir, f"{slug}-{version}.zip")
        
        logger.info(f"Targeting {name} (Version {version}) at {url}")
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Use stream=True to handle large files
                response = requests.get(url, stream=True, timeout=60, headers=headers)
                
                if response.status_code == 404:
                    logger.warning(f"Version {version} for {slug} returned 404. Trying next version...")
                    break # Break out of retry loop to try next version
                
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                logger.info(f"Downloading {slug}-{version}.zip (Size: {total_size / (1024*1024):.2f} MB)...")
                
                downloaded_size = 0
                with open(target_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                
                if downloaded_size > 0:
                    logger.info(f"Successfully downloaded {target_path}")
                    return True
                else:
                    logger.error(f"Downloaded file {target_path} is empty.")
                    
            except Exception as e:
                logger.error(f"Attempt {attempt} failed for {slug} v{version}: {e}")
                if attempt < MAX_RETRIES:
                    wait_time = 2 ** attempt
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All attempts failed for {slug} v{version}.")
        
        # If we reach here, either 404 or all retries failed for this version
        # Continue to next version in version_to_try
    
    return False

def main():
    if not os.path.exists(OUTPUT_BASE):
        os.makedirs(OUTPUT_BASE)
        logger.info(f"Created base directory: {OUTPUT_BASE}")

    success_count = 0
    for i, ds in enumerate(DATASETS):
        logger.info(f"--- Processing Dataset {i+1}/{len(DATASETS)}: {ds['name']} ---")
        if download_physionet_dataset(ds):
            success_count += 1
        
        # Rate limiting between datasets
        if i < len(DATASETS) - 1:
            logger.info(f"Rate limiting: waiting {RATE_LIMIT_DELAY}s...")
            time.sleep(RATE_LIMIT_DELAY)

    logger.info(f"MIMIC-IV Demo download process finished. {success_count}/{len(DATASETS)} datasets downloaded successfully.")

if __name__ == "__main__":
    main()
