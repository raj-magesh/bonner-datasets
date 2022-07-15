from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat
from brainio.stimulus_set import package

from .utils import load_conditions
from .constants import IDENTIFIER, N_SUBJECTS, FILENAMES


def package_stimulus_set(catalog_name: str, location_type: str, location: str, **kwargs) -> None:
    conditions = load_conditions()
    metadata = {}
    metadata["condition"] = conditions
    for subject in range(N_SUBJECTS):
        sets = loadmat(FILENAMES["cv_sets"][subject], simplify_cells=True)["sets"]
        cv_set = np.empty(len(conditions), dtype=np.int8)
        for i_set, set_ in enumerate(sets):
            cv_set[np.isin(conditions, set_)] = i_set
        metadata[f"cv_set_subject{subject}"] = cv_set
    metadata = pd.DataFrame.from_dict(metadata)

    paths = [path for path in sorted((Path("stimuli").rglob("*.*"))) if path.suffix in (".jpg", ".png")]
    stimulus_set = pd.DataFrame.from_dict(
        {
            "stimulus_id": [
                f"{path.stem}{path.parent.name.split('_')[0]}" for path in paths
            ],
            "filename": [str(path) for path in paths],
            "condition": [path.stem[:-3] for path in paths],
            "background": [path.parent.name.split("_")[0] for path in paths],
        }
    )
    stimulus_set = pd.merge(stimulus_set, metadata, on="condition")

    package(
        identifier=IDENTIFIER,
        stimulus_set=stimulus_set,
        stimulus_dir=Path.cwd(),
        catalog_name=catalog_name,
        location_type=location_type,
        location=location,
    )
