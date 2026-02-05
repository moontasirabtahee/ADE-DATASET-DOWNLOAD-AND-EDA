# coding: utf-8
# FAERS Data Downloader with Concurrency
# Downloads FAERS data from 2019Q1 to 2024Q4 (24 quarters)
# Uses concurrent downloads (4 quarters at a time)

import os
import re
import time
import shutil
import warnings
import requests
from tqdm import tqdm
from io import BytesIO
from zipfile import ZipFile
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.request import urlopen
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
target_page = ["https://fis.fda.gov/extensions/FPD-QDE-FAERS/FPD-QDE-FAERS.html"]
source_dir = "FAERS/FAERSsrc"
data_dir = "FAERS/FAERSdata"
MAX_WORKERS = 4  # Download 4 quarters concurrently

# Quarters to download (2019Q1 to 2024Q4)
TARGET_QUARTERS = []
for year in range(2019, 2025):
    for quarter in range(1, 5):
        TARGET_QUARTERS.append(f"{year % 100:02d}Q{quarter}")

# Ignore warnings
warnings.filterwarnings('ignore')


def download_single_file(file_name, url, source_dir, data_dir, pbar=None):
    """
    Download a single FAERS file.
    :param file_name: Name of the file to download
    :param url: URL of the file
    :param source_dir: FAERSsrc directory
    :param data_dir: FAERSdata directory
    :param pbar: tqdm progress bar object (optional)
    :return: tuple (file_name, success, error_message)
    """
    try:
        # Download with streaming for large files
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        content = BytesIO()
        total_size = int(response.headers.get('content-length', 0))
        
        for data in response.iter_content(chunk_size=1024*1024):
            content.write(data)
            
        download_size_mb = content.tell() / (1024 * 1024)
        
        # Extract ZIP
        z = ZipFile(content)
        
        # Extract to a temporary directory
        temp_dir = os.path.join(source_dir, file_name)
        os.makedirs(temp_dir, exist_ok=True)
        z.extractall(temp_dir)
        response.close()
        
        # Process files
        delete_unwanted_files(temp_dir)
        copied_count = copy_files(temp_dir, data_dir)
        
        # Clean up
        shutil.rmtree(temp_dir)
        
        if pbar:
            pbar.update(1)
            pbar.set_postfix_str(f"Last OK: {file_name}")
            
        return (file_name, True, f"{download_size_mb:.1f} MB, {copied_count} files")
    except Exception as e:
        error_msg = f"{str(e)}"
        if pbar:
            pbar.update(1)
            pbar.set_postfix_str(f"Last FAIL: {file_name}")
        return (file_name, False, error_msg)


def download_files_concurrent(faers_files, source_dir, data_dir, max_workers=4):
    """
    Download FAERS files concurrently.
    :param faers_files: dict of {file_name: url}
    :param source_dir: Source directory
    :param data_dir: Data directory
    :param max_workers: Number of concurrent downloads
    :return: none
    """
    total_files = len(faers_files)
    
    print(f"\n{'='*80}")
    print(f">> STARTING DATA DOWNLOAD ({total_files} Quarters)")
    print(f">> Max Concurrent Workers: {max_workers}")
    print(f"{'='*80}\n")
    
    results = {"success": [], "failed": []}
    
    with tqdm(total=total_files, desc="Overall Progress", unit="qtr", dynamic_ncols=True) as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_file = {
                executor.submit(download_single_file, file_name, url, source_dir, data_dir, pbar): file_name
                for file_name, url in faers_files.items()
            }
            
            # Process results as they complete
            for future in as_completed(future_to_file):
                file_name, success, info = future.result()
                
                if success:
                    results["success"].append((file_name, info))
                else:
                    results["failed"].append((file_name, info))
    
    # Print final summary
    print(f"\n{'='*80}")
    print(f">> DOWNLOAD SUMMARY")
    print(f"{'='*80}")
    print(f"Total Attempted: {total_files}")
    print(f"Successfully Processed: {len(results['success'])}")
    print(f"Failed: {len(results['failed'])}")
    
    if results['failed']:
        print(f"\n>> FAILED QUARTERS:")
        for fname, err in results['failed']:
            print(f"   [!] {fname}: {err}")
    
    if results['success']:
        print(f"\n>> RECENTLY DOWNLOADED (Last 5):")
        for fname, info in sorted(results['success'], reverse=True)[:5]:
            print(f"   [+] {fname}: {info}")
    
    print(f"{'='*80}\n")


def delete_unwanted_files(path):
    """
    Delete unwanted files (PDFs, DOCs, and specific file types).
    :param path: Directory path
    :return: count of deleted files
    """
    deleted = 0
    for parent, dirnames, filenames in os.walk(path):
        for fn in filenames:
            if fn.lower().endswith('.pdf') or fn.lower().endswith('.doc'):
                os.remove(os.path.join(parent, fn))
                deleted += 1
            elif fn.upper().startswith(("RPSR", "INDI", "THER", "SIZE", "STAT", "OUTC")):
                os.remove(os.path.join(parent, fn))
                deleted += 1
    return deleted


def copy_files(source_dir, data_dir):
    """
    Copy .txt files from source to data directory.
    :param source_dir: Source directory
    :param data_dir: Destination directory
    :return: count of copied files
    """
    copied = 0
    for root, dirs, files in os.walk(source_dir, topdown=False):
        for name in files:
            if name.lower().endswith('.txt'):
                source_path = os.path.join(root, name)
                dest_path = os.path.join(data_dir, name)
                shutil.move(source_path, dest_path)
                copied += 1
    return copied


def get_files_url():
    """
    Find all web URLs in the target page.
    :return: dict files = {"name":"url"}
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching FAERS file URLs...")
    files = {}
    
    for page_url in target_page:
        try:
            request = urlopen(page_url)
            page_bs = BeautifulSoup(request, "lxml")
            request.close()
        except:
            request = urlopen(page_url)
            page_bs = BeautifulSoup(request, "html.parser")
            request.close()
        
        for url in page_bs.find_all("a"):
            a_string = str(url)
            if "ASCII" in a_string.upper():
                t_url = url.get('href')
                file_name = str(url.get('href'))[-16:-4]
                files[file_name] = t_url
    
    # Save URLs to file
    save_path = os.path.join(os.getcwd(), "FaersFilesWebUrls.txt")
    with open(save_path, 'w') as f:
        for k in sorted(files.keys()):
            f.write(f"{k}:{files[k]}\n")
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Found {len(files)} FAERS files")
    return files


def filter_target_quarters(faers_files):
    """
    Filter files to only include target quarters (2019Q1-2024Q4).
    :param faers_files: All available FAERS files
    :return: Filtered dict of files
    """
    filtered = {}
    for file_name, url in faers_files.items():
        # Extract quarter identifier (e.g., "19Q1" from the file name)
        # File names are like "faers_ascii_2019Q1"
        for target_q in TARGET_QUARTERS:
            if target_q in file_name.upper():
                filtered[file_name] = url
                break
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Filtered to {len(filtered)} quarters (2019Q1-2024Q4)")
    return filtered




def main():
    """Main function to orchestrate the download process."""
    print(f"\n{'='*80}")
    print(f"FAERS Data Downloader (2019Q1 - 2024Q4)")
    print(f"Concurrent downloads: {MAX_WORKERS} at a time")
    print(f"{'='*80}\n")
    
    # Create directories if they don't exist
    os.makedirs(source_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Created directories:")
    print(f"  - Source: {os.path.abspath(source_dir)}")
    print(f"  - Data:   {os.path.abspath(data_dir)}\n")
    
    # Get all FAERS file URLs
    faers_files = get_files_url()
    
    # Filter to target quarters (2019Q1-2024Q4)
    target_files = filter_target_quarters(faers_files)
    
    if not target_files:
        print("ERROR: No files found for the target quarters (2019Q1-2024Q4)")
        print("Please check the FDA website and update the script if needed.")
        return
    
    print(f"\nQuarters to download:")
    for file_name in sorted(target_files.keys()):
        print(f"  - {file_name}")
    print()
    
    # Download files concurrently
    download_files_concurrent(target_files, source_dir, data_dir, MAX_WORKERS)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] All downloads completed!")
    print(f"Data saved to: {os.path.abspath(data_dir)}")


if __name__ == '__main__':
    main()
