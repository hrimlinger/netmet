"""correction TP4"""
import requests
import sys
import numpy as np

from collections import defaultdict
from pathlib import Path

from common.ripe.utils import get_coordinates_from_id
from common.credentials import get_ripe_atlas_credentials
from common.file_utils import dump_json, load_json, insert_json
from common.default import TP5_DATASET_PATH, TP5_RESULTS_PATH
from common.logger_config import logger


def get_measurement_description(measurement_id: int) -> dict:
    """
    retrieve a measurement using RIPE Atlas API, using a measurement uuid

    hints: requests package import
    """
    logger.info("###############################################")
    logger.info(f"# Get measurement description {measurement_id} #")
    logger.info("###############################################")
    base_url = "https://atlas.ripe.net/api/v2/measurements/"

    measurement_description = requests.get(f"{base_url}/{measurement_id}/").json()

    if not measurement_description:
        logger.error("Measurement description is empty")
        sys.exit(1)

    return measurement_description


def get_servers_from_country(country_code: str, out_file: Path) -> None:
    """get all connected servers from UA
    hints: we can add parameters to requests using the keyword params
    hints : params is a python dictionary
    """
    logger.info("###############################################")
    logger.info(f"# get_servers_from_country: {country_code}    ")
    logger.info("###############################################")

    base_url = "https://atlas.ripe.net/api/v2/probes/"

    # 1. set parameters
    params = {"country_code": country_code}

    if not params:
        logger.error("you must set parameters")
        sys.exit(1)
    else:
        # 2. perform request to get all RIPE Atlas servers in Ukraine
        response = requests.get(url=base_url, params=params).json()

        # 3. filter servers so they all :
        #   - have connected status (check the response)
        #   - have an IPv4 address
        filtered_vps = []
        for vp in response["results"]:
            if vp["status"]["name"] == "Connected":
                if vp["address_v4"]:
                    filtered_vps.append(vp)

        if filtered_vps:
            logger.info(
                f"Retrieved {len(filtered_vps)} connected servers from {country_code}"
            )
            dump_json(filtered_vps, out_file)
        else:
            logger.error("VP dataset empty")
            sys.exit(1)

    return filtered_vps


def ping(
    target: dict,
    vps: list,
    output_file_path: Path,
) -> int:
    """perform a traceroute from one vp in UA towards one server in RU"""
    logger.info("###############################################")
    logger.info("#  PING                                       #")
    logger.info("###############################################")

    ripe_credentials = get_ripe_atlas_credentials()

    if not ripe_credentials:
        raise RuntimeError(
            "set .env file at the root dir of the project with correct credentials"
        )

    response = requests.post(
        f"https://atlas.ripe.net/api/v2/measurements/?key={ripe_credentials['secret_key']}",
        json={
            "definitions": [
                {
                    "target": target,
                    "af": 4,
                    "packets": 3,
                    "size": 48,
                    "tags": ["netmetgeolocation"],
                    "description": f"Geolocation of target: {target}",
                    "resolve_on_probe": False,
                    "skip_dns_check": True,
                    "include_probe_id": False,
                    "type": "ping",
                }
            ],
            "probes": [{"value": vp, "type": "probes", "requested": 1} for vp in vps],
            "is_oneoff": True,
            "bill_to": ripe_credentials["username"],
        },
    ).json()

    measurement = {
        "measurement_id": response["measurements"],
    }

    logger.info(f"measurement uuid (for retrieval): {response['measurements']}")

    insert_json(measurement, output_file_path)

    return response["measurements"][0]


def dns(
    hostname: dict,
    vps: list,
    output_file_path: Path,
) -> int:
    """perform a DNS request from one vp in UA towards one server in RU"""
    logger.info("###############################################")
    logger.info("# DNS                                         #")
    logger.info("###############################################")

    ripe_credentials = get_ripe_atlas_credentials()

    if not ripe_credentials:
        raise RuntimeError(
            "set .env file at the root dir of the project with correct credentials"
        )

    response = requests.post(
        f"https://atlas.ripe.net/api/v2/measurements/?key={ripe_credentials['secret_key']}",
        json={
            "definitions": [
                {
                    "type": "dns",
                    "af": 4,
                    "resolve_on_probe": True,
                    "description": f"DNS measurement for {hostname}",
                    "query_class": "IN",
                    "query_type": "A",
                    "protocol": "UDP",
                    "udp_payload_size": 512,
                    "retry": 0,
                    "skip_dns_check": False,
                    "include_qbuf": False,
                    "include_abuf": True,
                    "prepend_probe_id": False,
                    "timeout": 5000,
                    "use_probe_resolver": False,
                    "set_nsid_bit": True,
                    "query_argument": f"{hostname}",
                    "target": "8.8.8.8",
                }
            ],
            "probes": [{"value": vp, "type": "probes", "requested": 1} for vp in vps],
            "is_oneoff": True,
            "bill_to": ripe_credentials["username"],
        },
    ).json()

    measurement = {
        "measurement_id": response["measurements"],
    }

    logger.info(f"measurement uuid (for retrieval): {response['measurements']}")

    insert_json(measurement, output_file_path)

    return response["measurements"][0]


def perform_measurements_dns(hostnames: list, vps: list, out_file_path: Path) -> list:
    """make measurement from a single vp toward a list of targets"""
    # first we will ping every addresses from France
    measurement_ids = []
    for hostname in hostnames:
        logger.info(f"performing DNS resolution for hostname: {hostname}")
        measurement_id = dns(
            hostname=hostname,
            vps=[vp["id"] for vp in vps],
            output_file_path=out_file_path,
        )
        measurement_ids.append(measurement_id)

    return measurement_ids


def retrieve_dns_measurements(measurement_descriptions: Path) -> list:
    """retrieve an save all measurements"""

    logger.info("###############################################")
    logger.info(f"# Retrieving all measurement results         #")
    logger.info("###############################################")
    pass


if __name__ == "__main__":
    # common to both methods
    find_vps = True
    measure = True
    retrieve_results = True

    # IP addresses to geolocate
    hostnames = ["www.google.com", "www.facebook.com", "www.bing.com"]

    # STEP 1:
    # select all VPs in France
    if find_vps:
        country_list = [
            "FR",
            "US",
        ]
        vps = []
        for country in country_list:
            vps_country = get_servers_from_country(
                country, TP5_DATASET_PATH / "vps_correction.json"
            )
            vps.extend(vps_country)

        dump_json(vps, TP5_DATASET_PATH / "vps_correction.json")

    # STEP 2:
    # Perform DNS measurement towards all hostnames and retrieve results
    if measure:
        vps = load_json(TP5_DATASET_PATH / "vps_correction.json")
        perform_measurements_dns(
            hostnames=hostnames,
            vps=vps,
            out_file_path=TP5_RESULTS_PATH
            / "dns_measurement_description_correction.json",
        )

    # STEP 3:
    # retrieve results
    if retrieve_results:
        measurement_descriptions = load_json(
            TP5_RESULTS_PATH / "dns_measurement_description_correction.json"
        )
        dns_resolution = retrieve_dns_measurements(
            measurement_descriptions=measurement_descriptions
        )
