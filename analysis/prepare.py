"""Keep only the chosen models and only the columns we need, in one small file.

Run:  python prepare.py "C:\\path\\to\\backblaze" data\\slice.csv.gz "MODEL ONE" "MODEL TWO"
(Copy the model names exactly as scan.py printed them.)
"""
import os
import sys

import pandas as pd

from load_data import EXTRA, ID_COLS, SHARED, iter_csvs, read_columns


def main(folder, out_path, models):
    parts, files = [], 0
    wanted = ID_COLS + SHARED + EXTRA
    for name, source in iter_csvs(folder):
        files += 1
        df = read_columns(source, wanted)
        df = df[df['model'].isin(models)]
        if len(df):
            parts.append(df)
        if files % 20 == 0:
            print(f'  ...read {files} files', flush=True)
    if not parts:
        sys.exit('No rows matched those model names. Copy them exactly from scan.py.')
    data = pd.concat(parts, ignore_index=True)
    missing = [c for c in SHARED + EXTRA if c not in data.columns]
    if missing:
        print('WARNING: these columns are not in your files and will be skipped:', missing)
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    data.to_csv(out_path, index=False, compression='gzip')
    print(f'Saved {len(data):,} rows, {data.serial_number.nunique():,} drives, '
          f'{int(data.failure.sum())} failures -> {out_path}')
    print('Date range:', data['date'].min(), 'to', data['date'].max())


if __name__ == '__main__':
    if len(sys.argv) < 4:
        sys.exit('Usage: python prepare.py <folder> <out.csv.gz> "MODEL" ["MODEL" ...]')
    main(sys.argv[1], sys.argv[2], sys.argv[3:])