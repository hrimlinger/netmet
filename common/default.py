"""main path for output files"""
from pathlib import Path

# Default path
DEFAULT_PATH: Path = Path(__file__).resolve().parent


##############################################################################################
# TP1                                                                                        #
##############################################################################################
TP1_PATH: Path = DEFAULT_PATH / "../TP1/"
TP1_DATASET_PATH: Path = TP1_PATH / "datasets"

# dataset
TP1_PROBES_PATH: Path = TP1_DATASET_PATH / "probes.json"
TP1_ANCHORS_PATH: Path = TP1_DATASET_PATH / "anchors.json"

# results
TP1_RESULTS_PATH: Path = TP1_PATH / "results"


##############################################################################################
# TP2                                                                                        #
##############################################################################################
TP2_PATH: Path = DEFAULT_PATH / "../TP2/"
TP2_DATASET_PATH: Path = TP2_PATH / "datasets"

# dataset
TP2_VPS_DATASET: Path = TP2_DATASET_PATH / "ua_vps.json"
TP2_TARGETS_DATASET: Path = TP2_DATASET_PATH / "ru_targets.json"

# datasets correction
TP2_VPS_DATASET_CORRECTION: Path = TP2_DATASET_PATH / "ua_vps_correction.json"
TP2_TARGETS_DATASET_CORRECTION: Path = TP2_DATASET_PATH / "ru_targets_correction.json"

# results
TP2_RESULTS_PATH: Path = TP2_PATH / "results"


##############################################################################################
# TP3                                                                                        #
##############################################################################################
TP3_PATH: Path = DEFAULT_PATH / "../TP3/"
TP3_DATASET_PATH: Path = TP3_PATH / "datasets"

# results
TP3_RESULTS_PATH: Path = TP3_PATH / "results"

##############################################################################################
# TP4                                                                                        #
##############################################################################################
TP4_PATH: Path = DEFAULT_PATH / "../TP4/"
TP4_DATASET_PATH: Path = TP4_PATH / "datasets"

# results
TP4_RESULTS_PATH: Path = TP4_PATH / "results"


##############################################################################################
# TP5                                                                                        #
##############################################################################################
TP5_PATH: Path = DEFAULT_PATH / "../TP5/"
TP5_DATASET_PATH: Path = TP5_PATH / "datasets"

# results
TP5_RESULTS_PATH: Path = TP5_PATH / "results"
