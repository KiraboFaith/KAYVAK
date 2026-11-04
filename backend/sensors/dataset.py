import json
from pathlib import Path

SUMMARY_PATH = Path(__file__).resolve().parent / 'data' / 'dataset_summary.json'


def load_summary(path=None):
    """The dataset summary made by analysis/export_summary.py, or None if it does not exist yet."""
    path = Path(path or SUMMARY_PATH)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))


def percentile_rank(value, points, quantiles):
    """Where a value sits among the dataset's drives: 0 = lowest, 100 = highest.

    quantiles[i] is the value at points[i] percent of the drives. Values between two
    saved points are worked out in a straight line between them.
    """
    if value <= quantiles[0]:
        return float(points[0])
    if value >= quantiles[-1]:
        return float(points[-1])
    for i in range(1, len(quantiles)):
        if value <= quantiles[i]:
            low, high = quantiles[i - 1], quantiles[i]
            if high == low:
                return float(points[i])
            return points[i - 1] + (points[i] - points[i - 1]) * (value - low) / (high - low)
    return float(points[-1])