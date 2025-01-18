# ~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~
#      /\_/\
#     ( o.o )
#      > ^ <
#
# Author: Johan Hanekom
# Date: January 2024
#
# ~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~

# =========== // STANDARD IMPORTS // ===========

from logging.handlers import RotatingFileHandler
import urllib.request
import subprocess
import logging
import re
import sys
import os

from typing import (
    List,
    Dict,
    Optional
)

# =========== // CONSTANTS// ===========

BASE_PATH: str = os.path.dirname(os.path.abspath(__file__))
PROG_NAME: str = os.path.basename(__file__)

LOG_DIR = "/var/log"
LOG_FILE = os.path.join(LOG_DIR, "healthcheck.log")

ALWAYS_HEALTHY: bool = str(os.getenv("ALWAYS_HEALTHY", "false")).lower() == "true"

SUPERVISOR_STATUS_IGNORE: List[str] = [
    "tail"
]

LINKS_TO_CHECK: List[str] = [
    "http://localhost:80/app-1"
]


# =========== // SIMPLE LOGGER SETUP // ===========

logger: logging.Logger = logging.getLogger(PROG_NAME)
logger.setLevel(logging.DEBUG)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)

if sys.platform != "win32":
    os.makedirs(LOG_DIR, exist_ok=True)
    file_handler = RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,  # Keep 5 backup files
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


# =========== // FUNCTIONS // ===========


def get_supervisor_status() -> Optional[List[Dict]]:
    try:
        result: subprocess.CompletedProcess = subprocess.run(
            ['supervisorctl', 'status'],
            capture_output=True,
            text=True,
            check=True
        )

        processes: List[Dict] = []
        for line in result.stdout.split('\n'):
            if line.strip():
                # Parse each line into components
                # Format is typically: name status pid
                parts: List[str] = re.split(
                    r'\s+',
                    line.strip(),
                    maxsplit=2
                )
                if len(parts) >= 2:
                    process: Dict[str, str] = {
                        'name': parts[0],
                        'status': parts[1],
                        'details': parts[2] if len(parts) > 2 else ''
                    }
                    processes.append(process)
        return processes
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running supervisorctl: {e}")
        logger.error(f"Error output: {e.stderr}")
        return None
    except FileNotFoundError:
        logger.error("supervisorctl command not found. Is supervisor installed?")
        return None


def check_ping(
    url: str
) -> bool:
    try:
        response = urllib.request.urlopen(url)
        return response.getcode() == 200
    except Exception:
        return False


def check_supervisor_all_running(
    processes: List[Dict],
    ignore: List[str] = SUPERVISOR_STATUS_IGNORE
) -> bool:
    if not processes:
        logger.critical("No processes to check")
        return False

    status: bool = True
    for supervisor_process in processes:
        if supervisor_process['name'] not in ignore:
            if supervisor_process['status'] == 'FATAL':
                logger.critical(f"{supervisor_process['name']} - FATAL - {supervisor_process['details']}")
                status = False
            else:
                logger.info(f"{supervisor_process['name']} - {supervisor_process['status']} - {supervisor_process['details']}")
    return status


if __name__ == "__main__":
    _p: str = "[CHECK]"
    logger.info(f"{_p} Starting healthcheck")

    # =========== // ALWAYS_HEALTHY // ===========

    if ALWAYS_HEALTHY:
        logger.info(f"{_p} ALWAYS_HEALTHY enabled")
        sys.exit(0)

    # =========== // CHECK SUPERVISOR // ===========

    processes: Optional[List[Dict]] = get_supervisor_status()
    if not processes:
        logger.critical(f"{_p} UNHEALTHY - Could not fetch supervisorctl status")
        sys.exit(1)

    if not check_supervisor_all_running(processes):
        sys.exit(1)

    # =========== // CHECK LINKS // ===========

    for url in LINKS_TO_CHECK:
        if check_ping(url):
            logger.info(f"{_p} {url} online")
        else:
            logger.critical(f"{_p} Can't reach {url}")
            sys.exit(1)

    # =========== // HEALTHY! // ===========

    logger.info(f"{_p} All GOOOOD!")
    sys.exit(0)
