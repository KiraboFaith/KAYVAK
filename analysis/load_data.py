"""Shared helpers for the Backblaze scripts. Not run directly: scan.py, prepare.py and train_test.py import it."""
import io
import os
import zipfile

import pandas as pd

# Columns we use. smart_N_raw = the raw counter of SMART attribute N.
SHARED = ['smart_9_raw', 'smart_193_raw', 'smart_194_raw']        # what the laptop can give us
EXTRA = ['smart_5_raw', 'smart_187_raw', 'smart_188_raw',
         'smart_197_raw', 'smart_198_raw']                         # laptop cannot give these (yet)
ID_COLS = ['date', 'serial_number', 'model', 'failure']


def iter_csvs(folder):
    """Yields (name, file_object) for every .csv under folder, including inside .zip files."""
    for root, _dirs, files in os.walk(folder):
        for name in sorted(files):
            path = os.path.join(root, name)
            if name.lower().endswith('.csv'):
                yield path, path
            elif name.lower().endswith('.zip'):
                with zipfile.ZipFile(path) as zf:
                    for member in sorted(zf.namelist()):
                        if member.lower().endswith('.csv') and '__MACOSX' not in member:
                            with zf.open(member) as handle:
                                yield f'{path}::{member}', io.BytesIO(handle.read())


def read_columns(source, wanted, chunksize=None):
    """Reads only the wanted columns that actually exist in this file."""
    header = pd.read_csv(source, nrows=0).columns
    if hasattr(source, 'seek'):
        source.seek(0)
    use = [c for c in wanted if c in header]
    return pd.read_csv(source, usecols=use, chunksize=chunksize, low_memory=False)