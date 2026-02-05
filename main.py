import subprocess
import sys
import os
import logging
import time
from datetime import datetime

# Configure logging
LOG_FILE = "download_orchestration.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# List of scripts to run in order
DOWNLOAD_SCRIPTS = [
    "download_sider.py",
    "download_drugbank.py",
    "download_omop.py",
    "download_synpuf_2.3m.py",
    "download_faers_concurrent.py"
]

def run_script(script_name):
    """Runs a python script as a subprocess and logs its output."""
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    
    if not os.path.exists(script_path):
        logger.error(f"Script not found: {script_path}")
        return False

    logger.info(f"{'='*60}")
    logger.info(f"STARTING: {script_name}")
    logger.info(f"{'='*60}")

    start_time = time.time()
    
    try:
        # Using sys.executable to ensure the same venv is used
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Print output in real-time
        for line in process.stdout:
            print(line, end='', flush=True)

        process.wait()
        
        end_time = time.time()
        duration = end_time - start_time
        
        if process.returncode == 0:
            logger.info(f"SUCCESS: {script_name} completed in {duration:.2f} seconds")
            return True
        else:
            logger.error(f"FAILED: {script_name} exited with code {process.returncode}")
            return False

    except Exception as e:
        logger.error(f"EXCEPTION while running {script_name}: {e}")
        return False

def main():
    logger.info("Initializing Data Download Orchestrator")
    logger.info(f"Scripts to execute: {', '.join(DOWNLOAD_SCRIPTS)}")
    
    total_scripts = len(DOWNLOAD_SCRIPTS)
    success_count = 0
    failure_count = 0
    
    start_all = time.time()

    for i, script in enumerate(DOWNLOAD_SCRIPTS, 1):
        logger.info(f"\nProcessing Task {i}/{total_scripts}...")
        
        if run_script(script):
            success_count += 1
        else:
            failure_count += 1
            # You can choose to stop on first failure or continue
            # logger.error("Stopping due to failure.")
            # break
            logger.warning(f"Moving to next script despite failure in {script}")

    end_all = time.time()
    total_duration = end_all - start_all

    logger.info(f"\n{'='*60}")
    logger.info("FINAL SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total Duration: {total_duration/60:.2f} minutes")
    logger.info(f"Total Scripts: {total_scripts}")
    logger.info(f"Successfully Completed: {success_count}")
    logger.info(f"Failed: {failure_count}")
    logger.info(f"{'='*60}")
    
    if failure_count == 0:
        logger.info("All downloads finished successfully!")
    else:
        logger.warning(f"Downloads finished with {failure_count} failures. Check {LOG_FILE} for details.")

if __name__ == "__main__":
    main()
