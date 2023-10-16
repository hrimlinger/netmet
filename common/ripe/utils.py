"""useful functions for working with response from RIPE Atlas"""
import time
import requests

from numpy import mean
from datetime import datetime

from common.logger_config import logger


def get_coordinates_from_addr(target_addr: str, targets: list) -> tuple:
    """return coordinates based on target IP address"""
    # get target geo
    for target in targets:
        if target_addr == target["address_v4"]:
            return target["geometry"]["coordinates"]


def get_coordinates_from_id(id: str, all_servers: list) -> tuple:
    """return coordinates based on target IP address"""
    # get target geo
    for server in all_servers:
        if id == server["id"]:
            return server["geometry"]["coordinates"]


def get_traceroute_countries(traceroute: list) -> None:
    """from a traceroute result, get countries"""
    parsed_traceroute = []

    # geoloc base url:
    geoloc_base_url = "https://stat.ripe.net/data/maxmind-geo-lite/data.json"

    for hop_results in traceroute:
        # get results metrics
        ttl = hop_results["hop"]
        responses = set()
        for result in hop_results["result"]:
            ttl = hop_results["hop"]

            # get all unique response for a given ttl
            if "from" in result:
                responses.add(result["from"])
            else:
                responses.add("*")

            # get country
            if len(responses) > 1 and "*" not in responses:
                logger.info("FIND ONEEEEE")

        for response in responses:
            # nothing to do with stars, just keep them in results
            if response == "*":
                parsed_traceroute.append(
                    {
                        "ttl": ttl,
                        "ip_addr": response,
                        "country": None,
                        "city": None,
                        "latitude": None,
                        "longitude": None,
                    }
                )
                logger.info(
                    f"ttl: {ttl} | ip addr : {response} | country: None | city : None | latitude : None | longitude : None"
                )
                continue

            params = {"resource": response}
            maxmind_data = requests.get(geoloc_base_url, params=params).json()

            maxmind_data = maxmind_data["data"]

            # if we do not have info about the ip address
            if maxmind_data["located_resources"]:
                located_resources = maxmind_data["located_resources"][0]["locations"][0]

                # save info
                parsed_traceroute.append(
                    {
                        "ttl": ttl,
                        "ip_addr": response,
                        "country": located_resources["country"],
                        "city": located_resources["city"],
                        "latitude": located_resources["latitude"],
                        "longitude": located_resources["longitude"],
                    }
                )

                logger.info(
                    f"ttl: {ttl} | ip addr : {response} | country: {located_resources['country']} | city : {located_resources['city']} | latitude : {located_resources['latitude']} | longitude : {located_resources['longitude']}"
                )
            else:
                parsed_traceroute.append(
                    {
                        "ttl": ttl,
                        "ip_addr": response,
                        "country": None,
                        "city": None,
                        "latitude": None,
                        "longitude": None,
                    }
                )
                logger.info(
                    f"ttl: {ttl} | ip addr : {response} | country: None | city : None | latitude : None | longitude : None"
                )

    return parsed_traceroute


def print_traceroute(traceroute_results: list) -> None:
    """print traceroute result nicely"""
    logger.info(f"TTL | results | rtt")

    for hop_results in traceroute_results:
        # get results metrics
        ttl = hop_results["hop"]
        response = ""
        rtts = []
        for result in hop_results["result"]:
            if "from" in result:
                response += " " + result["from"]
                if "rtt" in result:
                    rtts.append(result["rtt"])
            else:
                response += " *"

        # in case we only have stars (no answers)
        rtt = None
        if rtts:
            rtt = mean(rtts)

        # print metrics
        logger.info(f"{ttl} , {response} , {rtt}")


def get_date_from_str(date: str) -> datetime.date:
    """get datetime object from str var"""
    return datetime.strptime(date, "%d/%m/%Y %H:%M:%S")


def get_date_from_timestamp(timestamp: str) -> datetime.date:
    """return a datetime from a timestamp"""
    return datetime.fromtimestamp(timestamp)


def get_timestamp_from_date(date: str) -> str:
    """from a datetime format return unix timestamp"""
    if type(date) is str:
        date = datetime.strptime(date, "%d/%m/%Y %H:%M:%S")
    return int(time.mktime(date.timetuple()))


if __name__ == "__main__":
    start_time = datetime(2022, 2, 19)
    end_time = datetime(2022, 2, 25)

    start_time = get_timestamp_from_date(start_time)
    end_time = get_timestamp_from_date(end_time)

    print(start_time)
    print(end_time)


# perso_results = load_json(TP2_RESULTS_PATH / "perso_results.json")

# parsed_traceroutes = defaultdict(dict)
# for result in perso_results:
#     src = result["src_addr"]
#     dst = result["dst_addr"]
#     proto = result["proto"]
#     id = result["msm_id"]

#     traceroute = result["result"]

#     logger.info("############################################################")
#     logger.info(f"{src} -> {dst}, {id}, {proto}")
#     logger.info("############################################################")
#     parsed_traceroute = exo6_get_traceroute_countries(traceroute, id)

#     parsed_traceroutes[(src, dst)][proto] = parsed_traceroute

# dump_json(parsed_traceroutes, TP2_RESULTS_PATH / "perso_meshed_parsed.json")

# parsed_traceroute = load_json(TP2_RESULTS_PATH / "perso_meshed_parsed.json")

# for id in parsed_traceroute:
#     logger.info(id)
#     if "UDP" in parsed_traceroute[id] and "ICMP" in parsed_traceroute[id]:
#         logger.info("ICMP")
#         icmp_traceroute = parsed_traceroute[id]["ICMP"]
#         for hop in icmp_traceroute:
#             logger.info(
#                 f"ttl: {hop['ttl']} | ip addr : {hop['ip_addr']} | country: {hop['country']} | city : {hop['city']} | latitude : {hop['latitude']} | longitude : {hop['longitude']}"
#             )
#         logger.info("UDP")
#         udp_traceroute = parsed_traceroute[id]["UDP"]
#         for hop in udp_traceroute:
#             logger.info(
#                 f"ttl: {hop['ttl']} | ip addr : {hop['ip_addr']} | country: {hop['country']} | city : {hop['city']} | latitude : {hop['latitude']} | longitude : {hop['longitude']}"
#             )
