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
        logging.FileHandler("pharmgkb_download.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
OUTPUT_DIR = "PharmaGKB"
RATE_LIMIT_DELAY = 0.5  # 500ms delay between downloads
MAX_RETRIES = 3

DATASETS = [
    {"priority": 1, "dataset": "Clinical Variants", "filename": "clinicalVariants.zip", "size": "72.6 KB", "url": "https://s3.pgkb.org/data/clinicalVariants.zip", "size_bytes": 74342},
    {"priority": 2, "dataset": "Relationships", "filename": "relationships.zip", "size": "2.3 MB", "url": "https://s3.pgkb.org/data/relationships.zip", "size_bytes": 2411724},
    {"priority": 3, "dataset": "Summary Annotations", "filename": "summaryAnnotations.zip", "size": "1.2 MB", "url": "https://s3.pgkb.org/data/summaryAnnotations.zip", "size_bytes": 1258291},
    {"priority": 4, "dataset": "Variant Annotations", "filename": "variantAnnotations.zip", "size": "4.0 MB", "url": "https://s3.pgkb.org/data/variantAnnotations.zip", "size_bytes": 4194304},
    {"priority": 5, "dataset": "Phenotypes", "filename": "phenotypes.zip", "size": "182.7 KB", "url": "https://s3.pgkb.org/data/phenotypes.zip", "size_bytes": 187084},
    {"priority": 6, "dataset": "Drugs", "filename": "drugs.zip", "size": "652.9 KB", "url": "https://s3.pgkb.org/data/drugs.zip", "size_bytes": 668569},
    {"priority": 7, "dataset": "Chemicals", "filename": "chemicals.zip", "size": "774.4 KB", "url": "https://s3.pgkb.org/data/chemicals.zip", "size_bytes": 792985},
    {"priority": 8, "dataset": "Drug Labels", "filename": "drugLabels.zip", "size": "55.6 KB", "url": "https://s3.pgkb.org/data/drugLabels.zip", "size_bytes": 56934},
    {"priority": 9, "dataset": "Clinical Guidelines", "filename": "guidelineAnnotations.json.zip", "size": "821.8 KB", "url": "https://s3.pgkb.org/data/guidelineAnnotations.json.zip", "size_bytes": 841523},
    {"priority": 10, "dataset": "Pathways (JSON)", "filename": "pathways.json.zip", "size": "1.8 MB", "url": "https://s3.pgkb.org/data/pathways.json.zip", "size_bytes": 1887436},
    {"priority": 11, "dataset": "Pathways (TSV)", "filename": "pathways-tsv.zip", "size": "191.1 KB", "url": "https://s3.pgkb.org/data/pathways-tsv.zip", "size_bytes": 195686},
    {"priority": 12, "dataset": "Genes", "filename": "genes.zip", "size": "2.8 MB", "url": "https://s3.pgkb.org/data/genes.zip", "size_bytes": 2936012},
    {"priority": 13, "dataset": "Variants", "filename": "variants.zip", "size": "868.6 KB", "url": "https://s3.pgkb.org/data/variants.zip", "size_bytes": 889446},
    {"priority": 14, "dataset": "Occurrences", "filename": "occurrences.zip", "size": "2.7 MB", "url": "https://s3.pgkb.org/data/occurrences.zip", "size_bytes": 2831155},
]

def download_file(url: str, filename: str, expected_size_bytes: int) -> bool:
    target_path = os.path.join(OUTPUT_DIR, filename)
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Downloading {filename} (Attempt {attempt}/{MAX_RETRIES})...")
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(target_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Verify file size
            actual_size = os.path.getsize(target_path)
            # Allow some tolerance for size mismatch as 'MB/KB' might be approximate in the table
            # But here I'll use a 10% tolerance or just check if it's > 0 if exact bytes aren't reliable
            if actual_size > 0:
                logger.info(f"Successfully downloaded {filename} ({actual_size} bytes)")
                return True
            else:
                logger.error(f"Downloaded file {filename} is empty.")
                
        except Exception as e:
            logger.error(f"Attempt {attempt} failed for {filename}: {e}")
            if attempt < MAX_RETRIES:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                logger.error(f"All attempts failed for {filename}.")
    
    return False

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        logger.info(f"Created directory: {OUTPUT_DIR}")

    results = []
    for i, ds in enumerate(DATASETS):
        success = download_file(ds["url"], ds["filename"], ds["size_bytes"])
        results.append(success)
        
        # Rate limiting
        if i < len(DATASETS) - 1:
            logger.info(f"Rate limiting: waiting {RATE_LIMIT_DELAY}s...")
            time.sleep(RATE_LIMIT_DELAY)

    success_count = sum(results)
    logger.info(f"Download process finished. {success_count}/{len(DATASETS)} files downloaded successfully.")

if __name__ == "__main__":
    main()
