"""main correction TP3"""
"""execute each exercise or correction for TP1"""
import requests
import sys

from pathlib import Path

from common.credentials import get_ripe_atlas_credentials
from common.file_utils import dump_json, load_json, insert_json
from common.default import TP3_DATASET_PATH, TP3_RESULTS_PATH
from common.logger_config import logger

if __name__ == "__main__":
    ip_addresses_list = [
        {"address_v4": "142.250.201.4"},
        {"address_v4": "157.240.202.35"},
        {"address_v4": "142.250.188.228"},
    ]

    # Here goes your code for anycast detection, enjoy!
