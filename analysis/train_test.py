"""Label, split BY DRIVE, train, and measure honestly.

Run:  python train_test.py data\\slice.csv.gz            (warns 30 days ahead by default)
      python train_test.py data\\slice.csv.gz 14         (warns 14 days ahead)

It trains two models and compares them:
  SHARED  = only the numbers your laptop can also give (power-on hours, load cycles, temperature)
  FULL    = SHARED plus the extra SMART counters your laptop does not give yet
"""
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from load_data import EXTRA, SHARED

TARGET_FALSE_ALARM_RATE = 0.01   # we allow 1% of healthy drive-days to raise a false alarm
SEED = 42


def label(data, horizon):
    data = data.copy()
    data['date'] = pd.to_datetime(data['date'])
    fail_date = data[data.failure == 1].groupby('serial_number')['date'].min()
    data['fail_date'] = data['serial_number'].map(fail_date)
    data['days_to_failure'] = (data['fail_date'] - data['date']).dt.days
    last_day = data['date'].max()
    # A drive that never failed in our data might still fail just after the data ends,
    # so its last `horizon` days are unknown. Drop them instead of calling them healthy.
    unknown = data['fail_date'].isna() & (data['date'] > last_day - pd.Timedelta(days=horizon))
    data = data[~unknown].copy()
    data['target'] = ((data['days_to_failure'] >= 0) & (data['days_to_failure'] <= horizon)).astype(int)
    # Rows on the day of failure and after carry no warning value; keep days before failure only
    data = data[data['fail_date'].isna() | (data['days_to_failure'] > 0)]
    return data


def split_by_drive(data):
    """60% train / 20% validation / 20% test, whole drives only, failed drives spread evenly."""
    rng = np.random.default_rng(SEED)
    failed = data.loc[data.fail_date.notna(), 'serial_number'].unique()
    healthy = data.loc[data.fail_date.isna(), 'serial_number'].unique()
    assignment = {}
    for group in (failed, healthy):
        group = rng.permutation(group)
        cut1, cut2 = int(len(group) * 0.6), int(len(group) * 0.8)
        for i, serial in enumerate(group):
            assignment[serial] = 'train' if i < cut1 else 'val' if i < cut2 else 'test'
    part = data['serial_number'].map(assignment)
    return {name: data[part == name] for name in ('train', 'val', 'test')}


def fit_and_score(features, parts, horizon):
    features = [f for f in features if f in parts['train'].columns]
    prep = lambda df: df[features].fillna(-1)
    model = RandomForestClassifier(
        n_estimators=200, min_samples_leaf=20, class_weight='balanced_subsample',
        n_jobs=-1, random_state=SEED,
    ).fit(prep(parts['train']), parts['train']['target'])

    # Pick the alarm threshold on the VALIDATION drives, never on the test drives
    val = parts['val']
    val_scores = model.predict_proba(prep(val))[:, 1]
    healthy_scores = val_scores[val['fail_date'].isna().to_numpy()]
    threshold = np.quantile(healthy_scores, 1 - TARGET_FALSE_ALARM_RATE)

    test = parts['test'].copy()
    test['alarm'] = model.predict_proba(prep(test))[:, 1] > threshold

    failed = test[test.fail_date.notna()]
    caught, lead_times = 0, []
    for _serial, rows in failed.groupby('serial_number'):
        window = rows[(rows.days_to_failure <= horizon) & rows.alarm]
        if len(window):
            caught += 1
            lead_times.append(int(window.days_to_failure.max()))
    n_failed = failed['serial_number'].nunique()

    healthy = test[test.fail_date.isna()]
    drives_with_false_alarm = healthy.groupby('serial_number')['alarm'].any().mean()
    return {
        'features': features,
        'test_failed_drives': n_failed,
        'caught': caught,
        'recall': caught / n_failed if n_failed else float('nan'),
        'median_days_warning': float(np.median(lead_times)) if lead_times else float('nan'),
        'false_alarm_rate_per_healthy_day': float(healthy['alarm'].mean()),
        'healthy_drives_with_any_false_alarm': float(drives_with_false_alarm),
        'test_healthy_drives': healthy['serial_number'].nunique(),
    }


def main(path, horizon):
    data = pd.read_csv(path)
    data = label(data, horizon)
    parts = split_by_drive(data)
    print(f'Warning horizon: {horizon} days. Rows: ' + ', '.join(f'{k}={len(v):,}' for k, v in parts.items()))
    for name, part in parts.items():
        print(f'  {name}: {part.serial_number.nunique():,} drives, '
              f'{part[part.fail_date.notna()].serial_number.nunique()} that failed')
    if parts['test'][parts['test'].fail_date.notna()].serial_number.nunique() < 10:
        print('\nWARNING: fewer than 10 failed drives in the test set. Treat every number below as weak.')

    for name, features in (('SHARED (laptop can give these)', SHARED), ('FULL (adds counters the laptop lacks)', SHARED + EXTRA)):
        r = fit_and_score(features, parts, horizon)
        print(f'\n== {name} ==\n   features: {r["features"]}')
        print(f'   failed test drives caught early: {r["caught"]} of {r["test_failed_drives"]} '
              f'({r["recall"]:.0%}), median warning {r["median_days_warning"]:.0f} days')
        print(f'   false alarms: {r["false_alarm_rate_per_healthy_day"]:.2%} of healthy drive-days; '
              f'{r["healthy_drives_with_any_false_alarm"]:.0%} of {r["test_healthy_drives"]} healthy test drives raised at least one')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('Usage: python train_test.py <slice.csv.gz> [days_ahead]')
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 30)