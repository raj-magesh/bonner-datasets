from typing import Tuple
from pathlib import Path
from multiprocessing import Pool

from tqdm import tqdm
import boto3
import h5py
from PIL import Image

from .utils import (
    N_SUBJECTS,
    ROIS,
    N_SESSIONS,
    N_SESSIONS_HELD_OUT,
    N_STIMULI,
    BUCKET_NAME,
    format_image_id,
)


def download_dataset(force_download: bool = False, **kwargs) -> None:
    """Download the (1.8 mm)-resolution, GLMsingle preparation of the Natural Scenes Dataset.

    :param force: whether to force downloads even if files exist, defaults to False
    :type force: bool, optional
    """
    files = [
        "nsddata_stimuli/stimuli/nsd/nsd_stimuli.hdf5",  # stimulus images
        "nsddata/experiments/nsd/nsd_stim_info_merged.csv",  # stimulus metadata
    ]
    for subject in range(N_SUBJECTS):
        for roi_type in ("surface", "volume"):
            for roi_group in ROIS[roi_type]:
                for hemisphere in ("lh", "rh"):
                    files.append(
                        f"nsddata/ppdata/subj{subject + 1:02}/func1pt8mm/roi/{hemisphere}.{roi_group}.nii.gz"
                    )  # roi masks

                # roi labels
                if roi_type == "surface":
                    files.append(
                        f"nsddata/freesurfer/subj{subject + 1:02}/label/{roi_group}.mgz.ctab"
                    )
                elif roi_type == "volume":
                    files.append(f"nsddata/templates/{roi_group}.ctab")

        # TODO once the later sessions are released, remove the N_SESSIONS_HELD_OUT
        for session in range(N_SESSIONS[subject] - N_SESSIONS_HELD_OUT):
            files.append(
                f"nsddata_betas/ppdata/subj{subject + 1:02}/func1pt8mm/betas_fithrf_GLMdenoise_RR/betas_session{session + 1:02}.hdf5"
            )  # betas
        for suffix in ("", "_split1", "_split2"):
            files.append(
                f"nsddata_betas/ppdata/subj{subject + 1:02}/func1pt8mm/betas_fithrf_GLMdenoise_RR/ncsnr{suffix}.nii.gz"
            )  # ncsnr
        files.extend(
            [
                f"nsddata/ppdata/subj{subject + 1:02}/func1pt8mm/T1_to_func1pt8mm.nii.gz",
                f"nsddata/ppdata/subj{subject + 1:02}/func1pt8mm/brainmask.nii.gz",
            ]
        )

    s3 = boto3.client("s3")
    for file in [Path.cwd() / file for file in files]:
        if force_download or not file.exists():
            file.parent.mkdir(exist_ok=True, parents=True)
            with open(file, "wb") as f:
                s3.download_fileobj(BUCKET_NAME, file, f)


def _save_image(args: Tuple[Image.Image, Path]) -> None:
    """Save an image to a filepath.

    :param args: an image and the filepath it should be saved to
    :type args: Tuple[Image.Image, Path]
    """
    image, filepath = args
    if not filepath.exists():
        image.save(filepath)


def save_images(**kwargs) -> None:
    """Save HDF5-formatted image stimuli as PNG files."""

    stimuli = h5py.File(
        Path.cwd() / "nsddata_stimuli" / "stimuli" / "nsd" / "nsd_stimuli.hdf5", "r"
    )["imgBrick"]

    images_dir = Path("images")
    images_dir.mkdir(parents=True, exist_ok=True)
    image_paths = [images_dir / f"{format_image_id(image)}.png" for image in range(N_STIMULI)]
    images = (
        Image.fromarray(stimuli[stimulus, :, :, :])
        for stimulus in range(stimuli.shape[0])
    )
    with Pool() as pool:
        list(
            pool.imap(
                _save_image,
                tqdm(
                    zip(images, image_paths),
                    total=len(image_paths),
                    desc="images",
                ),
                chunksize=1000,
            ),
        )
