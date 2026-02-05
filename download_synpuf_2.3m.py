import os
import boto3
import requests
import zipfile
from botocore import UNSIGNED
from botocore.client import Config
from tqdm import tqdm

# Constants
ATHENA_URL = "https://athena.ohdsi.org/api/v1/vocabularies/zip/bd0f3268-9c87-4194-a551-6ec8e18264f7"
OUTPUT_DIR = "SynPUF2.3M"
BUCKET_NAME = "synpuf-omop"
S3_PREFIX = "cmsdesynpuf2.3/"

def download_omop_vocab(output_dir):
    print(f"\n--- Starting OMOP Vocabulary Download ---")
    
    vocab_zip_path = os.path.join(output_dir, "omop_vocab.zip")
    
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    print(f"Downloading vocabularies from {ATHENA_URL}")
    
    try:
        # Download the file
        response = requests.get(ATHENA_URL, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 1024 # 1MB chunks
        
        with open(vocab_zip_path, 'wb') as f, tqdm(
            desc="Downloading Vocab Zip",
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(block_size):
                size = f.write(data)
                bar.update(size)
                
        print("\nDownload finished. Extracting files...")
        
        # Extract files
        with zipfile.ZipFile(vocab_zip_path, 'r') as zip_ref:
            # Get list of files in zip
            for file_info in zip_ref.infolist():
                print(f"Extracting {file_info.filename}...")
                zip_ref.extract(file_info, output_dir)
            
        print(f"Extraction complete. Vocab files saved in {output_dir}")
        
        # Optional: Remove the zip file after extraction to save space
        # os.remove(vocab_zip_path) 
        
    except requests.exceptions.RequestException as e:
        print(f"Error downloading vocab file: {e}")
    except zipfile.BadZipFile:
        print("Error: The downloaded vocab file is not a valid zip file.")
    except Exception as e:
        print(f"An error occurred during vocab download: {e}")

def download_synpuf_2_3m(output_dir):
    print(f"\n--- Starting SynPUF 2.3M Data Download ---")
    
    os.makedirs(output_dir, exist_ok=True)

    # Initialize S3 client for unsigned access (public bucket)
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED), region_name='us-east-1')
    
    print(f"Listing files in s3://{BUCKET_NAME}/{S3_PREFIX} ...")
    
    try:
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=S3_PREFIX)
        
        files_to_download = []
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    size = obj['Size']
                    # Skip the directory marker itself
                    if key.endswith('/'):
                        continue
                    files_to_download.append({'key': key, 'size': size})
        
        print(f"Found {len(files_to_download)} SynPUF files to download.")
        
        # Download files
        for i, file_info in enumerate(files_to_download):
            key = file_info['key']
            total_size = file_info['size']
            filename = os.path.basename(key)
            local_path = os.path.join(output_dir, filename)
            
            # Skip if already downloaded and size matches
            if os.path.exists(local_path):
                local_size = os.path.getsize(local_path)
                if local_size == total_size:
                    print(f"[{i+1}/{len(files_to_download)}] Skipping {filename} (already exists)")
                    continue
            
            print(f"[{i+1}/{len(files_to_download)}] Downloading {filename} ({total_size / (1024*1024):.2f} MB)")
            
            with tqdm(total=total_size, unit='B', unit_scale=True, unit_divisor=1024, desc=filename) as pbar:
                s3.download_file(
                    Bucket=BUCKET_NAME,
                    Key=key,
                    Filename=local_path,
                    Callback=lambda bytes_transferred: pbar.update(bytes_transferred)
                )
                
        print("\nAll SynPUF downloads completed successfully.")
        
    except Exception as e:
        print(f"An error occurred during SynPUF download: {e}")

if __name__ == "__main__":
    # Step 1: Download Vocabularies
    download_omop_vocab(OUTPUT_DIR)
    
    # Step 2: Download SynPUF Data
    download_synpuf_2_3m(OUTPUT_DIR)
