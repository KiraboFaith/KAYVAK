"""Which drive models have enough failures to learn from?

Run:  python scan.py "C:\\path\\to\\backblaze"
Prints a table; you pick 2 or 3 models from it for prepare.py.
"""
import sys

import pandas as pd

from load_data import iter_csvs, read_columns


def main(folder):
    days, fails, files = {}, {}, 0
    for name, source in iter_csvs(folder):
        files += 1
        df = read_columns(source, ['model', 'failure'])
        grouped = df.groupby('model')['failure'].agg(['count', 'sum'])
        for model, row in grouped.iterrows():
            days[model] = days.get(model, 0) + int(row['count'])
            fails[model] = fails.get(model, 0) + int(row['sum'])
        if files % 20 == 0:
            print(f'  ...read {files} files', flush=True)
    if not files:
        sys.exit('No .csv files (or .zip files containing .csv) found in that folder.')
    table = pd.DataFrame({'drive_days': pd.Series(days), 'failures': pd.Series(fails)})
    table = table.sort_values('failures', ascending=False)
    print(f'\nRead {files} files. Models with the most failures:\n')
    print(table.head(20).to_string())
    print('\nPick models with at least ~50 failures. Fewer than that gives results you cannot trust.')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: python scan.py <folder with the Backblaze csv/zip files>')
    main(sys.argv[1])