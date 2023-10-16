"""main correction TP3"""
import requests
import time
import sys

from collections import defaultdict
from pathlib import Path

from common.ripe.utils import get_coordinates_from_id
from common.geoloc import distance, rtt_to_km
from common.credentials import get_ripe_atlas_credentials
from common.file_utils import dump_json, load_json, insert_json
from common.default import TP3_DATASET_PATH, TP3_RESULTS_PATH
from common.logger_config import logger


def get_measurement_description(measurement_id: int) -> dict:
    """
    retrieve a measurement using RIPE Atlas API, using a measurement uuid

    hints: requests package import
    """
    logger.info("###############################################")
    logger.info(f"# Get measuremet description {measurement_id} #")
    logger.info("###############################################")
    base_url = "https://atlas.ripe.net/api/v2/measurements/"

    measurement_description: dict = requests.get(f"{base_url}/{measurement_id}/").json()

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
                    "tags": ["netmetAnycastDetection"],
                    "description": f"Netmet anycast detection for target {target}",
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


def make_measurements(targets: list, vps: list, out_file_path: Path) -> list:
    """make measurement from a single vp toward a list of targets"""
    # first we will ping every addresses from France
    measurement_ids = []
    for target in targets:
        measurement_id = ping(
            target=target["address_v4"],
            vps=[vp["id"] for vp in vps],
            output_file_path=out_file_path,
        )
        measurement_ids.append(measurement_id)

    return measurement_ids


def retrieve_measurement_results(measurement_ids: list) -> list:
    """retrieve measurement results from a list of ids"""
    # for each measurements, retrieve results
    measurement_results = []
    for measurement in measurement_ids:
        measurement_id = measurement["measurement_id"][0]

        measurement_description = get_measurement_description(measurement_id)

        measurement_results_url = measurement_description["result"]

        req_results = requests.get(measurement_results_url).json()

        measurement_results.append(req_results)

    return measurement_results


def get_ping_results(measurement_results: list) -> None:
    """print all ping for manual analysis"""

    ping_results_per_dst = defaultdict(dict)
    for results in measurement_results:
        for result in results:
            src_addr = result["src_addr"]
            dst_addr = result["dst_addr"]

            ping_results = result["result"]

            rtts = []
            for ping_result in ping_results:
                if "rtt" in ping_result:
                    rtts.append(ping_result["rtt"])

            # get the lowest rtt
            if rtts:
                ping_results_per_dst[src_addr][dst_addr] = min(rtts)

    # print results
    for src in ping_results_per_dst:
        for dst, min_rtt in ping_results_per_dst[src].items():
            logger.info(f"src addr: {src}; dst_addr: {dst}; min rtt: {min_rtt}")

    return ping_results_per_dst


def get_max_distance_vps_to_target(results: dict) -> dict:
    """for each ping results get higher bound distance between vps and targets"""
    distances = defaultdict(list)
    for measurement_results in results:
        for measurement in measurement_results:
            target_addr = measurement["dst_addr"]
            vp_addr = measurement["src_addr"]
            ping_results = measurement["result"]

            # find min rtt between target and vp
            rtts = []
            for ping_result in ping_results:
                if "rtt" in ping_result:
                    rtts.append(ping_result["rtt"])

            # get the lowest rtt
            if rtts:
                min_rtt = min(rtts)  # get the lowest latency
                vp_to_target_max_distance = rtt_to_km(
                    min_rtt
                )  # convert this latency into distance

                # store results
                distances[target_addr].append((vp_addr, vp_to_target_max_distance))

    return distances


if __name__ == "__main__":
    ip_addresses_list = [
        {"address_v4": "142.250.201.4"},
        {"address_v4": "157.240.202.35"},
        {"address_v4": "104.16.124.96"},
        {"address_v4": "142.250.188.228"},
    ]

    # first we get servers spaced together, here I chose servers in FR and US
    make_measurement = False
    if make_measurement:
        retrieve_servers = False
        # if we do not have the server yet
        if retrieve_servers:
            ripe_vps_fr = get_servers_from_country(
                "FR", out_file=TP3_DATASET_PATH / "ripe_vp_fr_correction.json"
            )
            ripe_vps_us = get_servers_from_country(
                "US", out_file=TP3_DATASET_PATH / "ripe_vp_us_correction.json"
            )
        # once server retrieval done, just load results
        else:
            ripe_vps_fr = load_json(TP3_DATASET_PATH / "ripe_vp_fr_correction.json")
            ripe_vps_us = load_json(TP3_DATASET_PATH / "ripe_vp_us_correction.json")

        # perform a ping from each vps to each target
        measurement_ids_fr = make_measurements(
            targets=ip_addresses_list,
            vps=ripe_vps_fr,
            out_file_path=TP3_RESULTS_PATH / "pings_fr_correction.json",
        )

        logger.info(f"Measurement ids for France: {measurement_ids_fr}")

        # same but from the US
        measurement_ids_us = make_measurements(
            targets=ip_addresses_list,
            vps=ripe_vps_us,
            out_file_path=TP3_RESULTS_PATH / "pings_us_correction.json",
        )

        logger.info(f"Measurement ids for USA: {measurement_ids_us}")

        # time to wait for accessing measurement results on RIPE Atlas API
        time.sleep(60 * 3)

    # finally we retrieve the results and print them
    retrieve_results = False
    ping_results = dict()
    if retrieve_results:
        measurement_ids_fr = load_json(TP3_RESULTS_PATH / "pings_fr_correction.json")
        measurement_ids_us = load_json(TP3_RESULTS_PATH / "pings_us_correction.json")

        measurement_results_fr = retrieve_measurement_results(measurement_ids_fr)
        measurement_results_us = retrieve_measurement_results(measurement_ids_us)

        dump_json(
            measurement_results_fr,
            TP3_RESULTS_PATH / "measurement_results_fr_correction.json",
        )
        dump_json(
            measurement_results_us,
            TP3_RESULTS_PATH / "measurement_results_us_correction.json",
        )

    # analyze the results we obtained
    make_analysis = True
    if make_analysis:
        ripe_vps_fr: dict = load_json(TP3_DATASET_PATH / "ripe_vp_fr_correction.json")
        ripe_vps_us: dict = load_json(TP3_DATASET_PATH / "ripe_vp_us_correction.json")

        measurement_results_fr = load_json(
            TP3_RESULTS_PATH / "measurement_results_fr_correction.json"
        )
        measurement_results_us = load_json(
            TP3_RESULTS_PATH / "measurement_results_us_correction.json"
        )

        logger.info("FR results")
        ping_results_fr = get_ping_results(measurement_results_fr)
        logger.info("US results")
        ping_results_us = get_ping_results(measurement_results_us)

        # get distances between vps and targets
        logger.info("Getting distances between vps and target")
        distance_vps_to_target_fr = get_max_distance_vps_to_target(
            measurement_results_fr
        )

        logger.info("Getting distances between vps and target")
        distance_vps_to_target_us = get_max_distance_vps_to_target(
            measurement_results_us
        )

        # better if we combined them
        all_estimated_distances = distance_vps_to_target_fr
        all_estimated_distances.update(distance_vps_to_target_us)

        logger.info("Get inter-vps distances")

        # get distance between vps and vps
        distance_inter_vps = {}
        all_vps = ripe_vps_fr
        all_vps.extend(ripe_vps_us)

        for vp in all_vps:
            vp_lon, vp_lat = vp["geometry"]["coordinates"]

            for next_vp in all_vps:
                if next_vp["address_v4"] == vp["address_v4"]:
                    continue

                next_vp_lon, next_vp_lat = next_vp["geometry"]["coordinates"]

                # store distance for each pair of targets
                distance_inter_vps[
                    (vp["address_v4"], next_vp["address_v4"])
                ] = distance(
                    lat1=vp_lat,
                    lat2=next_vp_lat,
                    lon1=vp_lon,
                    lon2=next_vp_lon,
                )

        logger.info("Anycast address detection based on speed of light violation")

        # finally for each targets and estimated distance, check for speed of light violation
        anycast_addresses = set()
        for target_addr, vps_to_target_distance in all_estimated_distances.items():
            for vp, estimated_distance in vps_to_target_distance:
                for next_vp, next_estimated_distance in vps_to_target_distance:
                    if next_vp == vp:
                        continue

                    # some ip addresses mismatch happens with RIPE Atlas
                    # servers are described with private address while results are given with public one
                    # TODO: only use probe id to identify probes, it works every time
                    try:
                        distance_vps = distance_inter_vps[(vp, next_vp)]
                    except KeyError as e:
                        continue

                    # condition for speed of light violation
                    if estimated_distance + next_estimated_distance < distance_vps:
                        anycast_addresses.add(target_addr)

        logger.info(
            f"Anycast addresses: {anycast_addresses} (original set of ip addresses: {ip_addresses_list})"
        )
