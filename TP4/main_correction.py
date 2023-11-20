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


def perform_measurements(targets: list, vps: list, out_file_path: Path) -> list:
    """make measurement from a single vp toward a list of targets"""
    logger.info("###############################################")
    logger.info(f"# Pinging all targets from all vps           #")
    logger.info("###############################################")

    # first we will ping every addresses from a list of vps
    measurement_ids = []
    for target in targets:
        measurement_id = ping(
            target=target["address_v4"],
            vps=[vp["id"] for vp in vps],
            output_file_path=out_file_path,
        )
        measurement_ids.append(measurement_id)

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


def retrieve_geolocation_measurements(measurement_descriptions: Path) -> list:
    """retrieve an save all measurements"""

    logger.info("###############################################")
    logger.info(f"# Retrieving all measurement results         #")
    logger.info("###############################################")

    # for each target find results
    vps_to_target_min_rtts = defaultdict(list)
    for measurement in measurement_descriptions:
        measurement_ids = measurement["measurement_id"]

        for measurement_id in measurement_ids:
            # get measurement results url
            measurement_description = get_measurement_description(measurement_id)

            results_url = measurement_description["result"]

            # get measurement results
            measurement_results = requests.get(results_url).json()

            # retrieve each minimum rtt per pair vp/target
            for result in measurement_results:
                vp_id = result["prb_id"]
                target_addr = result["dst_addr"]
                pring_results = result["result"]

                min_rtt = None
                rtts = []
                for ping_result in pring_results:
                    if "rtt" in ping_result:
                        rtts.append(ping_result["rtt"])

                # it might happens that we do not get results
                if rtts:
                    min_rtt = min(rtts)
                else:
                    continue

                logger.info(target_addr)
                vps_to_target_min_rtts[target_addr].append((vp_id, min_rtt))

    # save results
    dump_json(
        vps_to_target_min_rtts,
        TP4_RESULTS_PATH / "vps_to_target_min_rtt_correction.json",
    )

    return vps_to_target_min_rtts


# for each target, do geolocation
def shortest_ping_geolocation(
    vps_to_target_min_rtts: dict, vps: list, output_path: Path
) -> dict:
    """from a set of measurement, return the estimated geolocation using shortest ping method"""

    logger.info("###############################################")
    logger.info(f"# Geolocation estimation with: Shortest ping #")
    logger.info("###############################################")

    geolocation_per_target = {}
    for target, min_rtts_list in vps_to_target_min_rtts.items():
        logger.info(f"shortest ping validation for target: {target}")
        # shortest ping
        best_vp_addr, _ = min(min_rtts_list, key=lambda x: x[1])
        target_coordinates_shortest_ping = get_coordinates_from_id(best_vp_addr, vps)

        target_lon, target_lat = target_coordinates_shortest_ping

        geolocation_per_target[target] = {
            "lat": target_lat,
            "lon": target_lon,
        }

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

    geolocation_per_target = {}
    for target, min_rtts_list in vps_to_target_min_rtts.items():
        # load vps coordinates
        vps_coordinates = {}
        for vp in vps:
            vp_lon = vp["geometry"]["coordinates"][0]
            vp_lat = vp["geometry"]["coordinates"][1]
            vps_coordinates[vp["id"]] = (vp_lat, vp_lon)

        # load results
        vp_min_rtts = {}
        for vp_addr, min_rtt in min_rtts_list:
            # find
            vp_min_rtts[vp_addr] = min_rtt

        # perform cbg
        target_coordinates_cbg = cbg(
            target_ip=target,
            vp_coordinates_per_ip=vps_coordinates,
            rtt_per_vp_to_target=vp_min_rtts,
        )

        target_lat, target_lon = target_coordinates_cbg

        geolocation_per_target[target] = {
            "lat": target_lat,
            "lon": target_lon,
        }

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

    error_distances = {}
    for target_addr, coordinates in geolocation_per_target.items():
        estimated_lat = coordinates["lat"]
        estimated_lon = coordinates["lon"]

        # find true (lat; lon)
        for data in validation_dataset:
            if target_addr == data["address_v4"]:
                true_lat = data["lat"]
                true_lon = data["lon"]

        # compute error distance
        error_distance = distance(
            lat1=estimated_lat,
            lat2=true_lat,
            lon1=estimated_lon,
            lon2=true_lon,
        )

        error_distances[target_addr] = error_distance

    # save results in output path
    dump_json(error_distances, output_path)

    return error_distances


if __name__ == "__main__":
    # common to both methods
    find_vps = True
    measure = True
    retrieve_results = True

    # geolocation
    geolocate_shortest_ping = True
    geolocate_cbg = True

    # validation
    shortest_ping_validation = True
    cbg_validation = True

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
        vps = get_servers_from_country("FR", TP4_DATASET_PATH / "vps_correction.json")

    # STEP 2:
    # Ping each target from each VPs
    if measure:
        vps = load_json(TP4_DATASET_PATH / "vps_correction.json")
        perform_measurements(
            targets=targets,
            vps=vps,
            out_file_path=TP4_RESULTS_PATH
            / "ping_measurement_description_correction.json",
        )

    # STEP 3:
    # retrieve results
    if retrieve_results:
        measurement_descriptions = load_json(
            TP4_RESULTS_PATH / "ping_measurement_description_correction.json"
        )
        vps_to_target_min_rtts = retrieve_geolocation_measurements(
            measurement_descriptions=measurement_descriptions
        )

    # STEP 4:
    # perform shortest ping geolocation
    if geolocate_shortest_ping:
        # load vps
        vps = load_json(TP4_DATASET_PATH / "vps_correction.json")

        # load min rtts
        vps_to_target_min_rtts = load_json(
            TP4_RESULTS_PATH / "vps_to_target_min_rtt_correction.json"
        )

        geolocation_per_target_shortest_ping = shortest_ping_geolocation(
            vps_to_target_min_rtts=vps_to_target_min_rtts,
            vps=vps,
            output_path=TP4_RESULTS_PATH
            / "target_geolocation_shortest_ping_correction.json",
        )

    # STEP 5:
    # perform cbg geolocation
    if geolocate_cbg:
        # load min rtts
        vps_to_target_min_rtts = load_json(
            TP4_RESULTS_PATH / "vps_to_target_min_rtt_correction.json"
        )

        geolocation_per_target_cbg = cbg_geolocation(
            vps_to_target_min_rtts=vps_to_target_min_rtts,
            vps=vps,
            output_path=TP4_RESULTS_PATH / "target_geolocation_cbg_correction.json",
        )

    # STEP 6:
    # perform shortest ping validation

    # load results and true data
    validation_dataset = load_json(TP4_DATASET_PATH / "validation_dataset.json")

    if shortest_ping_validation:
        geolocation_shortest_ping = load_json(
            TP4_RESULTS_PATH / "target_geolocation_shortest_ping_correction.json"
        )

        geolocation_error_shortest_ping = evaluate_geolocation(
            geolocation_per_target=geolocation_shortest_ping,
            validation_dataset=validation_dataset,
            output_path=TP4_RESULTS_PATH
            / "geolocation_error_shortest_ping_correction.json",
        )

        logger.info(
            f"median error shortest ping: {np.median([error for error in geolocation_error_shortest_ping.values()])} [km]"
        )

    if cbg_validation:
        geolocation_cbg = load_json(
            TP4_RESULTS_PATH / "target_geolocation_cbg_correction.json"
        )
        geolocation_error_cbg = evaluate_geolocation(
            geolocation_per_target=geolocation_cbg,
            validation_dataset=validation_dataset,
            output_path=TP4_RESULTS_PATH / "geolocation_error_cbg_correction.json",
        )

        logger.info(
            f"median error cbg: {np.median([error for error in geolocation_error_cbg.values()])} [km]"
        )
