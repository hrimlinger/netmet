"""Functions to load and save data into a json format.
All the paths are given in default.py file.
"""
import pickle

import ujson as json
from pathlib import Path


def load_json(file_path: Path):
    """load data at input path"""
    with open(file_path) as f:
        return json.load(f)


def dump_json(data: list, file_path: Path):
    """dump data to output file"""
    # check that dirs exits
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)


def insert_json(data: dict, file_path: Path) -> None:
    """insert into json struct"""
    existing_data = []

    if file_path.exists():
        with file_path.open("r") as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                pass

    with file_path.open("w") as f:
        if type(data) == list:
            existing_data.extend(data)
        if type(data) == dict:
            existing_data.append(data)
        json.dump(existing_data, f, indent=4)


def load_pickle(file_path: Path) -> None:
    """load data from pickle file"""
    with open(file_path, "rb") as f:
        return pickle.load(f)


def dump_pickle(data: list, file_path: Path):
    """dum data with pickle to output file path"""
    # check that dirs exits
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "wb") as f:
        pickle.dump(data, f)


if __name__ == "__main__":
    t = [1, 2, 3, 4]
    insert_json(t, Path("test.json"))
    insert_json(t, Path("test.json"))
