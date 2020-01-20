import re
import os
import csv

from collections import OrderedDict

import nrrd
import shutil

import numpy as np
import pandas as pd
import scipy.io as sio

from pathlib import Path
from natsort import natsorted


def relative_paths(path_to_dir, target_format=None):
    """Produce a list of relative paths to all files in directory."""

    if target_format is None:
        raise ValueError('Must specify target format')

    if not os.path.isdir(path_to_dir):
        raise RuntimeError('Invalid path {}'.format(path_to_dir))

    # Apply natural sorting to filenames.
    file_names = natsorted(os.listdir(path_to_dir))

    rel_paths = []
    for fname in file_names:

        rel_path = os.path.join(path_to_dir, fname)
        if os.path.isfile(rel_path) and rel_path.endswith(target_format):
            rel_paths.append(rel_path)

    return rel_paths


def _sample_num(sample):
    # Extracts patient ID.
    digit_in_str = re.findall(r'\d+', os.path.basename(sample))

    if len(digit_in_str) > 1:
        raise RuntimeError('Filename can only contain 1 number sequenze')

    return int(digit_in_str[0])


def sample_paths(path_image_dir, path_mask_dir, target_format=None):
    """Generate dictionary of locations to image and corresponding masks."""

    image_paths = relative_paths(path_image_dir, target_format=target_format)
    mask_paths = relative_paths(path_mask_dir, target_format=target_format)

    images_and_mask_paths = []
    for image_path in image_paths:

        # Match sample with mask by number.
        mask = None
        image_num = _sample_num(image_path)
        for mask_path in mask_paths:
            if _sample_num(mask_path) == image_num:
                images_and_mask_paths.append(
                    OrderedDict(
                        Image=image_path,
                        Mask=mask_path,
                        Patient=image_num,
                        Reader=''
                    )
                )
    return images_and_mask_paths


def read_prelim_result(path_to_file):
    """Read temporary stored results."""

    results = pd.read_csv(path_to_file, index_col=False)

    return OrderedDict(zip(*(results.columns, results.values[0])))


def write_prelim_results(path_to_file, results):
    """Store results in temporary separate files to prevent write conflicts."""

    with open(path_to_file, 'w') as outfile:
        writer = csv.DictWriter(
            outfile, fieldnames=list(results.keys()), lineterminator='\n'
        )
        writer.writeheader()
        writer.writerow(results)

    return None


def write_final_results(path_to_file, results):
    """Write the total collection of results to disk."""

    if isinstance(results, pd.DataFrame):
        results.to_csv(path_to_file)

    elif isinstance(results, (list, tuple, np.ndarray)):
        data = pd.DataFrame([result for result in results])
        data.to_csv(path_to_file)

    else:
        raise TypeError(f'Invalid type {type(results)} of results.')


def setup_tempdir(tempdir, root=None):
    """Returns path and sets up directory if non-existent."""

    if root is None:
        root = os.getcwd()

    path_tempdir = os.path.join(root, tempdir)
    if not os.path.isdir(path_tempdir):
        os.mkdir(path_tempdir)

    return path_tempdir


def teardown_tempdir(path_to_dir):
    """Removes directory even if not empty."""

    shutil.rmtree(path_to_dir)

    return None
