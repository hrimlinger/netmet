"""correction TP4"""
import requests
import sys
import numpy as np

from collections import defaultdict
from pathlib import Path

from common.geoloc import distance, cbg
from common.ripe.utils import get_coordinates_from_id
from common.credentials import get_ripe_atlas_credentials
from common.file_utils import dump_json, load_json, insert_json
from common.default import TP4_DATASET_PATH, TP4_RESULTS_PATH
from common.logger_config import logger


def get_servers_from_country(
    country_code: str,
    out_file: Path,
) -> list:
    """get all connected servers from UA
    hints: we can add parameters to requests using the keyword params
    hints : params is a python dictionary
    """
    logger.info("###############################################")
    logger.info(f"# get_servers_from_country: {country_code}    ")
    logger.info("###############################################")

    base_url = "https://atlas.ripe.net/api/v2/probes/"

    # find all vps that are  connected within a country
    filtered_vps = []

    # save results in file for future use
    dump_json(filtered_vps, out_file)

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


def perform_measurements(
    targets: list,
    vps: list,
    out_file_path: Path,
) -> list:
    """make measurement from a single vp toward a list of targets"""
    logger.info("###############################################")
    logger.info(f"# Pinging all targets from all vps           #")
    logger.info("###############################################")

    # perform pings from all vps towards every targets
    measurement_ids = []

    return measurement_ids


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


def retrieve_geolocation_measurements(
    measurement_descriptions: Path,
    out_path: Path,
) -> list:
    """retrieve an save all measurements"""

    logger.info("###############################################")
    logger.info(f"# Retrieving all measurement results         #")
    logger.info("###############################################")

    # for each target, get all vps/min_rtt
    # suggested data structure:
    # vps_to_target_min_rtts[target] = [(vp1, min_rtt) , (vp2, min_rtt), ...]
    vps_to_target_min_rtts = defaultdict(list)

    # save results
    dump_json(
        vps_to_target_min_rtts,
        out_path,
    )

    return vps_to_target_min_rtts


def shortest_ping_geolocation(
    vps_to_target_min_rtts: dict, vps: list, output_path: Path
) -> dict:
    """from a set of measurement, return the estimated geolocation using shortest ping method"""

    logger.info("###############################################")
    logger.info(f"# Geolocation estimation with: Shortest ping #")
    logger.info("###############################################")

    # for each target, perform shortest ping geolocation
    # using the results you obtained previously
    # (i.e.: for each target find coordinates of the vp with the lowest rtt)
    geolocation_per_target = {}

    # save results
    dump_json(
        geolocation_per_target,
        output_path,
    )

    return geolocation_per_target


def cbg_geolocation(
    vps_to_target_min_rtts: dict,
    vps: dict,
    output_path: Path,
) -> dict:
    """from a set of measurement, return the estimated geolocation using shortest ping method"""

    logger.info("###############################################")
    logger.info(f"# Geolocation estimation with: CBG           #")
    logger.info("###############################################")

    # for each target, perform shortest ping geolocation
    # using the results you obtained previously
    # (i.e.: for each target perform the cbg method (see import functions))
    geolocation_per_target = {}

    # save results
    dump_json(
        geolocation_per_target,
        output_path,
    )


def evaluate_geolocation(
    geolocation_per_target: dict,
    validation_dataset: list,
    output_path: Path,
) -> dict:
    """from a set of geolocation estimation and their true geolocation return the error in kilometers"""

    logger.info("###############################################")
    logger.info(f"# Geolocation Evaluation                     #")
    logger.info("###############################################")

    # compare the geolocation you found with the validation one
    error_distances = {}

    # save results in output path
    dump_json(error_distances, output_path)

    return error_distances


if __name__ == "__main__":
    # common to both methods
    find_vps = True
    measure = False
    retrieve_results = False

    # geolocation
    geolocate_shortest_ping = False
    geolocate_cbg = False

    # validation
    shortest_ping_validation = False
    cbg_validation = False

    # IP addresses to geolocate
    targets = [
        {"address_v4": "132.227.123.30"},
        {"address_v4": "134.214.181.60"},
        {"address_v4": "185.155.93.186"},
        {"address_v4": "139.124.244.54"},
    ]

    # STEP 1:
    # select all VPs in France
    if find_vps:
        vps = get_servers_from_country("FR", TP4_DATASET_PATH / "vps.json")

    # STEP 2:
    # Ping each target from each VPs
    if measure:
        vps = load_json(TP4_DATASET_PATH / "vps.json")
        perform_measurements(
            targets=targets,
            vps=vps,
            out_file_path=TP4_RESULTS_PATH / "ping_measurement_description.json",
        )

    # STEP 3:
    # retrieve results
    if retrieve_results:
        measurement_descriptions = load_json(
            TP4_RESULTS_PATH / "ping_measurement_description.json"
        )
        vps_to_target_min_rtts = retrieve_geolocation_measurements(
            measurement_descriptions=measurement_descriptions,
            out_path=TP4_DATASET_PATH / "vps_to_target_min_rtt.json",
        )

    # STEP 4:
    # perform shortest ping geolocation
    if geolocate_shortest_ping:
        # load vps
        vps = load_json(TP4_DATASET_PATH / "vps.json")

        # load min rtts
        vps_to_target_min_rtts = load_json(
            TP4_RESULTS_PATH / "vps_to_target_min_rtt.json"
        )

        geolocation_per_target_shortest_ping = shortest_ping_geolocation(
            vps_to_target_min_rtts=vps_to_target_min_rtts,
            vps=vps,
            output_path=TP4_RESULTS_PATH / "target_geolocation_shortest_ping.json",
        )

    # STEP 5:
    # perform cbg geolocation
    if geolocate_cbg:
        # load min rtts
        vps_to_target_min_rtts = load_json(
            TP4_RESULTS_PATH / "vps_to_target_min_rtt.json"
        )

        geolocation_per_target_cbg = cbg_geolocation(
            vps_to_target_min_rtts=vps_to_target_min_rtts,
            vps=vps,
            output_path=TP4_RESULTS_PATH / "target_geolocation_cbg.json",
        )

    # STEP 6:
    # perform shortest ping validation

    # load results and true data
    validation_dataset = load_json(TP4_DATASET_PATH / "validation_dataset.json")

    if shortest_ping_validation:
        geolocation_shortest_ping = load_json(
            TP4_RESULTS_PATH / "target_geolocation_shortest_ping.json"
        )

        geolocation_error_shortest_ping = evaluate_geolocation(
            geolocation_per_target=geolocation_shortest_ping,
            validation_dataset=validation_dataset,
            output_path=TP4_RESULTS_PATH / "geolocation_error_shortest_ping.json",
        )

        logger.info(
            f"median error shortest ping: {np.median([error for error in geolocation_error_shortest_ping.values()])} [km]"
        )

    if cbg_validation:
        geolocation_cbg = load_json(TP4_RESULTS_PATH / "target_geolocation_cbg.json")
        geolocation_error_cbg = evaluate_geolocation(
            geolocation_per_target=geolocation_cbg,
            validation_dataset=validation_dataset,
            output_path=TP4_RESULTS_PATH / "geolocation_error_cbg.json",
        )

        logger.info(
            f"median error cbg: {np.median([error for error in geolocation_error_cbg.values()])} [km]"
        )
