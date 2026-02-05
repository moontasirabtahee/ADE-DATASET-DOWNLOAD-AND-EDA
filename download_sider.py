import os
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
SIDER_DIR = "SIDER"
BASE_URL = "http://sideeffects.embl.de/media/download/"

FILES_TO_DOWNLOAD = [
    "README",
    "drug_names.tsv",
    "drug_atc.tsv",
    "meddra_all_se.tsv.gz",
    "meddra_freq.tsv.gz",
    "meddra_all_label_se.tsv.gz",
    "meddra_all_indications.tsv.gz",
    "meddra.tsv.gz"
]

def download_file(filename):
    url = f"{BASE_URL}{filename}"
    target_path = os.path.join(SIDER_DIR, filename)
    
    try:
        logger.info(f"Downloading {filename}...")
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(target_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        size_mb = os.path.getsize(target_path) / (1024 * 1024)
        logger.info(f"Successfully downloaded {filename} ({size_mb:.2f} MB)")
        return True
    except Exception as e:
        logger.error(f"Failed to download {filename}: {e}")
        return False

def main():
    if not os.path.exists(SIDER_DIR):
        os.makedirs(SIDER_DIR)
        logger.info(f"Created directory: {SIDER_DIR}")

    success_count = 0
    for filename in FILES_TO_DOWNLOAD:
        if download_file(filename):
            success_count += 1
            
    logger.info(f"Download complete. {success_count}/{len(FILES_TO_DOWNLOAD)} files downloaded.")

if __name__ == "__main__":
    main()
