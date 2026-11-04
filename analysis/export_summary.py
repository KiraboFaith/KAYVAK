"""Summarise the prepared Backblaze slice so the website can compare a laptop drive with it.

Run:  python export_summary.py data\\slice_st12.csv.gz
Writes: ..\\backend\\sensors\\data\\dataset_summary.json  (a small file, safe to commit)
"""
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent.parent / 'backend' / 'sensors' / 'data' / 'dataset_summary.json'
POINTS = list(range(0, 101, 5))   # we keep the value at 0%, 5%, 10% ... 100% of the drives
METRICS = {                        # name used by the website -> Backblaze column
    'power_on_hours': 'smart_9_raw',
    'load_unload_cycles': 'smart_193_raw',
    'temperature': 'smart_194_raw',
}


def last_reading_per_drive(data):
    data = data.copy()
    data['date'] = pd.to_datetime(data['date'])
    return data.sort_values('date').groupby('serial_number').tail(1)


def quantiles(values):
    return [round(float(v), 1) for v in np.percentile(values, POINTS)]


def clean(series, name):
    values = series.dropna()
    if name == 'temperature':
        # Some makers pack extra numbers (min/max temperature) into the higher bytes of this
        # counter. The real temperature sits in the lowest byte.
        values = values.astype('int64') & 0xFF
    return values


def main(path):
    data = pd.read_csv(path)
    failed_serials = set(data.loc[data.failure == 1, 'serial_number'])
    last = last_reading_per_drive(data)
    is_failed = last['serial_number'].isin(failed_serials)

    summary = {
        'source': 'Backblaze Drive Stats',
        'models': sorted(data['model'].unique().tolist()),
        'date_from': str(data['date'].min()),
        'date_to': str(data['date'].max()),
        'healthy_drives': int((~is_failed).sum()),
        'failed_drives': int(is_failed.sum()),
        'created': date.today().isoformat(),
        'points': POINTS,
        'metrics': {},
    }
    for name, column in METRICS.items():
        if column not in last.columns:
            print(f'WARNING: column {column} is not in your data, skipping {name}')
            continue
        healthy = clean(last.loc[~is_failed, column], name)
        failed = clean(last.loc[is_failed, column], name)
        if len(healthy) == 0:
            print(f'WARNING: no healthy values for {name}, skipping')
            continue
        summary['metrics'][name] = {
            'healthy': quantiles(healthy),
            'failed': quantiles(failed) if len(failed) else None,
        }
        print(f'{name}: median healthy drive = {np.median(healthy):,.0f}'
              + (f', median failed drive = {np.median(failed):,.0f}' if len(failed) else ''))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=1), encoding='utf-8')
    print(f'\nSaved {OUT}')
    print('Check the medians above look sensible (temperature about 20-50, hours in the thousands).')
    print('If one looks absurd, tell me before using the website panel.')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: python export_summary.py <slice.csv.gz>')
    main(sys.argv[1])