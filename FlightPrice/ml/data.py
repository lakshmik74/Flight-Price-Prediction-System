import pandas as pd
import os

_cached = {}
_REQUIRED_COLUMNS = {
    'Date_of_Journey',
    'Dep_Time',
    'Arrival_Time',
    'Duration',
    'Total_Stops',
    'Airline',
    'Source',
    'Destination',
    'Additional_Info',
    'Price',
}


def validate_dataset_schema(df, required_columns=None):
    if required_columns is None:
        required_columns = _REQUIRED_COLUMNS
    missing = sorted(set(required_columns) - set(df.columns))
    if missing:
        raise ValueError(
            'Dataset schema validation failed. Missing required columns: ' +
            ', '.join(missing) +
            '. Please upload a dataset with the expected columns.'
        )
    return True


def load_dataset(path=None):
    global _cached
    if path is None:
        # Try common candidate locations (prefer data/raw/ for reorganized project)
        candidates = [
            # repository root data/raw (works when running from project root)
            os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'raw', 'FlightPrice.csv')),
            # legacy / reorganized locations
            os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'FlightPrice.csv')),
            os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Dataset', 'FlightPrice.csv')),
            os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Dataset', 'FlightPrice.csv')),
        ]
        path = None
        for p in candidates:
            if os.path.exists(p):
                path = p
                break
        if path is None:
            path = candidates[0]

    if path in _cached:
        return _cached[path]

    if not os.path.exists(path):
        raise FileNotFoundError(f'Dataset file not found: {path}')

    df = pd.read_csv(path)
    validate_dataset_schema(df)
    _cached[path] = df
    return df

def get_dataset():
    return load_dataset()
