# -*- coding: utf-8 -*-
#
# feature_extraction.py
#

"""
Extraction of radiomics image features.

The feature extraction procedure assumes a parameter file and a list with
references to all images samples. Extracted features are stored in a temporary
directory created immideately after execution and deleted after the process is
complete. If the process was incomplete, the temporary directory presist.
Hence, it is possible to re-enter an aborted process from last stored results.
"""

__author__ = 'Severin Langberg'
__email__ = 'langberg91@gmail.com'


import os
import csv
import time

from copy import copy
from datetime import datetime
from collections import OrderedDict

import shutil
import logging
import radiomics
import threading

import numpy as np
import pandas as pd
import SimpleITK as sitk

from joblib import Parallel, delayed
from multiprocessing import cpu_count
from radiomics.featureextractor import RadiomicsFeaturesExtractor

import utils



# Time limit limit for each task to complete.
TIMEOUT = int(1e4)

# Names of directories storing errors and temporary results.
ERROR_DIR = 'errors'
TMP_FEATURE_DIR = 'tmp_feature_extraction'

threading.current_thread().name = 'Main'


def _check_is_file(path_to_file):
    # Checks if file exists.
    if os.path.isfile(path_to_file):
        return
    else:
        raise ValueError('Not recognized as file: {}'.format(path_to_file))


def feature_extractor(param_file, 
                      paths_to_images_and_masks, 
                      path_to_results,
                      verbose=0, 
                      n_jobs=None):
    """Extract features from images using the PyRadimoics package.
    
    Preliminary results are stored for re-entering the process in case of
    abortion.

    Args:
        param_file (str):
        samples (list):

    Kwargs:
        verbose (int): The level of verbosity during extraction.
        n_jobs (int): The number of CPUs to distribute the extraction process.
            Defaults to available - 1.
    Returns:
        (dict): The extracted image features.
    """

    global TMP_FEATURE_DIR, TIMEOUT

    _check_is_file(param_file)

    # Setup temporary directory to store preliminary results.
    path_tempdir = utils.setup_tempdir(TMP_FEATURE_DIR)

    # Set number of available CPUs.
    if n_jobs is None:
        n_jobs = cpu_count() - 1 if cpu_count() > 1 else cpu_count()

    if verbose > 0:
        print('Initiated feature extraction.')

    # Extract features.
    results = Parallel(n_jobs=n_jobs, verbose=verbose, timeout=TIMEOUT)(
        delayed(_extract_features)(
            param_file=param_file, 
            case=path_to_images_and_masks, 
            path_tempdir=path_tempdir, 
            verbose=verbose
        ) for path_to_images_and_masks in paths_to_images_and_masks
    )
    # Write extracted features to disk.
    utils.write_final_results(path_to_results, results)
    # Clean up temporary directory after procedure is complete.
    utils.teardown_tempdir(TMP_FEATURE_DIR)


def _extract_features(param_file, case, path_tempdir, verbose=0):
    # Extracts features from a single image sample.

    features = OrderedDict(case)
    ptLogger = logging.getLogger('radiomics.batch')

    try:
        threading.current_thread().name = case['Patient']

        case_file = ('_').join(('features', str(case['Patient']), '.csv'))
        path_case_file = os.path.join(path_tempdir, case_file)

        # Load results stored prior to process abortion.
        if os.path.isfile(path_case_file):
            features = utils.read_prelim_result(path_case_file)

            if verbose > 1:
                print('Loading previously extracted features.')

            ptLogger.info('Case %s already processed', case['Patient'])

        # Extract features.
        else:

            extractor = RadiomicsFeaturesExtractor(param_file)

            if verbose > 1:
                print('Extracting features.')

            start_time = datetime.now()
            features.update(
                extractor.execute(case['Image'], case['Mask']),
                label=case.get('Label', None)
            )
            delta_time = datetime.now() - start_time

            if verbose > 1:
                print('Writing preliminary results.')

            # Write preliminary results to disk.
            utils.write_prelim_results(path_case_file, features)

            delta_t = datetime.now() - start_time
            ptLogger.info('Case %s processed in %s', case['Patient'], delta_t)

    except Exception:
        ptLogger.error('Feature extraction failed!', exc_info=True)

    return features