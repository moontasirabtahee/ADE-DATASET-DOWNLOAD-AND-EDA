import os
import requests
from tqdm import tqdm
import zipfile

URL = "https://athena.ohdsi.org/api/v1/vocabularies/zip/bd11e931-3565-4b56-8f49-8876860947ba"
OUTPUT_DIR = "omop vocab"
ZIP_FILE = os.path.join(OUTPUT_DIR, "omop_vocab.zip")

def download_and_extract(url, zip_path, extract_to):
    # Create directory
    if not os.path.exists(extract_to):
        os.makedirs(extract_to)
        print(f"Created directory: {extract_to}")

    print(f"Starting download from {url}")
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 1024 # 1MB chunks
        
        with open(zip_path, 'wb') as f, tqdm(
            desc="Downloading",
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(block_size):
                size = f.write(data)
                bar.update(size)
                
        print("\nDownload finished. Extracting files...")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
            
        print(f"Extraction complete. Files saved in {extract_to}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")
    except zipfile.BadZipFile:
        print("Error: The downloaded file is not a valid zip file.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    download_and_extract(URL, ZIP_FILE, OUTPUT_DIR)
