import os
import re
import time
import joblib
import numpy as np
from datetime import datetime

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
except Exception:
    plt = None
    PdfPages = None

try:
    from sklearn.preprocessing import LabelEncoder, MinMaxScaler
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.tree import DecisionTreeRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
except Exception as sklearn_import_error:
    LabelEncoder = None
    MinMaxScaler = None
    RandomForestRegressor = None
    GradientBoostingRegressor = None
    LinearRegression = None
    DecisionTreeRegressor = None
    train_test_split = None
    mean_absolute_error = None
    mean_squared_error = None
    r2_score = None
    _SKLEARN_IMPORT_ERROR = sklearn_import_error
else:
    _SKLEARN_IMPORT_ERROR = None

from .data import load_dataset
from .features import prepare_feature_frame

try:
    from xgboost import XGBRegressor
except ImportError:
    XGBRegressor = None

try:
    from lightgbm import LGBMRegressor
except ImportError:
    LGBMRegressor = None

try:
    from catboost import CatBoostRegressor
except ImportError:
    CatBoostRegressor = None

_ARTIFACT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'models'))
os.makedirs(_ARTIFACT_DIR, exist_ok=True)
_PRODUCTION_MODEL_PATH = os.path.join(_ARTIFACT_DIR, 'production_model.joblib')
_BEST_MODEL_PATH = os.path.join(_ARTIFACT_DIR, 'best_model.joblib')
_SCALER_PATH = os.path.join(_ARTIFACT_DIR, 'scaler.joblib')
_META_PATH = os.path.join(_ARTIFACT_DIR, 'model_metadata.joblib')
_REPORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'reports'))
os.makedirs(_REPORT_DIR, exist_ok=True)


def _require_ml_runtime():
    if _SKLEARN_IMPORT_ERROR is not None:
        raise RuntimeError(f'ML dependencies are unavailable in this environment: {_SKLEARN_IMPORT_ERROR}')
    if any(symbol is None for symbol in [LabelEncoder, MinMaxScaler, RandomForestRegressor, GradientBoostingRegressor, LinearRegression, DecisionTreeRegressor, train_test_split, mean_absolute_error, mean_squared_error, r2_score]):
        raise RuntimeError('The scikit-learn runtime could not be initialized in this environment.')


def _find_dataset_path():
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'FlightPrice.csv')),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Dataset', 'FlightPrice.csv')),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Dataset', 'FlightPrice.csv')),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


def _get_dataset_version():
    path = _find_dataset_path()
    if os.path.exists(path):
        return f"{os.path.basename(path)}@{int(os.path.getmtime(path))}"
    return 'unknown'


def _supported_models():
    _require_ml_runtime()
    models = {
        'linear_regression': LinearRegression(),
        'decision_tree': DecisionTreeRegressor(random_state=42),
        'random_forest': RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1),
        'gradient_boosting': GradientBoostingRegressor(random_state=42),
    }
    if XGBRegressor is not None:
        models['xgboost'] = XGBRegressor(n_estimators=150, random_state=42, verbosity=0, n_jobs=-1)
    if LGBMRegressor is not None:
        models['lightgbm'] = LGBMRegressor(n_estimators=150, random_state=42, n_jobs=-1)
    if CatBoostRegressor is not None:
        models['catboost'] = CatBoostRegressor(iterations=150, random_state=42, verbose=0)
    return models


def _safe_label_transform(encoder, value):
    value = str(value).strip()
    if not value:
        return 0
    if value in encoder.classes_:
        return int(encoder.transform([value])[0])
    return 0


def _build_input_row(enc, scaler, airline, source, dest, dd, mm, yy):
    import pandas as pd

    row = {
        'Airline': str(airline or '').strip(),
        'Source': str(source or '').strip(),
        'Destination': str(dest or '').strip(),
        'day': int(dd),
        'month': int(mm),
        'year': int(yy),
        'day_of_week': int(pd.Timestamp(f"{yy}-{mm}-{dd}").dayofweek),
        'dep_hour': 0,
        'dep_minute': 0,
        'arrival_hour': 0,
        'arrival_minute': 0,
        'duration_minutes': 0,
    }

    feat_cols = enc['feature_cols']
    encoders = enc.get('encoders', {})
    arr = []
    for c in feat_cols:
        if c in encoders:
            arr.append(_safe_label_transform(encoders[c], row.get(c, '')))
        else:
            arr.append(float(row.get(c, 0)))

    arr = np.array(arr, dtype=float).reshape(1, -1)
    return scaler.transform(arr)


def _encode_features(frame):
    encoders = {}
    for col in ['Airline', 'Source', 'Destination', 'Additional_Info']:
        if col in frame.columns:
            encoder = LabelEncoder()
            frame[col] = encoder.fit_transform(frame[col].astype(str))
            encoders[col] = encoder
    return frame, encoders


def _normalize_model_name(model_name):
    return re.sub(r'[^A-Za-z0-9]+', '_', str(model_name).strip().lower()).strip('_')


def _next_model_version(model_name):
    normalized = _normalize_model_name(model_name)
    highest = 0
    for model_file in os.listdir(_ARTIFACT_DIR):
        match = re.match(rf'^v(\d+)_({re.escape(normalized)})\.joblib$', model_file)
        if match and match.group(2) == normalized:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def _save_pdf_report(report, candidate_models, best_model):
    pdf_path = os.path.join(_REPORT_DIR, 'model_comparison.pdf')
    with PdfPages(pdf_path) as pdf:
        summary_lines = [
            'Flight Price Model Comparison Report',
            '',
            f"Generated: {report.get('generated_at', datetime.utcnow().isoformat())}",
            f"Dataset version: {report.get('dataset_version', 'unknown')}",
            f"Rows: {report.get('rows', 0)}",
            f"Feature count: {len(report.get('features', []))}",
            f"Training time: {report.get('training_time_seconds', 0.0):.2f} seconds",
            '',
            f"Best model: {best_model.get('name', 'N/A')} ({best_model.get('model_version', 'N/A')})",
            f"Best metrics: RMSE={best_model.get('rmse', 0.0):.2f}, MAE={best_model.get('mae', 0.0):.2f}, R2={best_model.get('r2', 0.0):.4f}",
            '',
            'Notes:',
            report.get('notes', ''),
        ]
        fig = plt.figure(figsize=(11, 8.5))
        fig.patch.set_facecolor('white')
        for idx, line in enumerate(summary_lines):
            fig.text(0.05, 0.95 - idx * 0.035, line, fontsize=11, family='sans-serif')
        pdf.savefig(fig)
        plt.close(fig)

        if candidate_models:
            headings = ['Model', 'Version', 'RMSE', 'MAE', 'R2']
            table_data = []
            for item in candidate_models:
                table_data.append([
                    item.get('name', 'N/A'),
                    item.get('model_version', 'N/A'),
                    f"{item.get('rmse', 0.0):.2f}",
                    f"{item.get('mae', 0.0):.2f}",
                    f"{item.get('r2', 0.0):.4f}",
                ])
            fig = plt.figure(figsize=(11, 8.5))
            ax = fig.add_subplot(111)
            ax.axis('off')
            tbl = ax.table(cellText=table_data, colLabels=headings, loc='center', cellLoc='center')
            tbl.auto_set_font_size(False)
            tbl.set_fontsize(10)
            tbl.auto_set_column_width(col=list(range(len(headings))))
            ax.set_title('Candidate model comparison', pad=20, fontsize=14, weight='bold')
            pdf.savefig(fig)
            plt.close(fig)

    return pdf_path


def _save_eda_report(df):
    report = {
        'generated_at': datetime.utcnow().isoformat(),
        'dataset_version': _get_dataset_version(),
        'rows': len(df),
        'columns': df.columns.tolist(),
        'missing_values': df.isna().sum().to_dict(),
        'unique_values': {col: int(df[col].nunique()) for col in ['Airline', 'Source', 'Destination', 'Route'] if col in df.columns},
        'price': {
            'mean': float(df['Price'].mean()),
            'median': float(df['Price'].median()),
            'min': float(df['Price'].min()),
            'max': float(df['Price'].max()),
            'std': float(df['Price'].std()),
        },
    }
    report_path = os.path.join(_REPORT_DIR, 'eda_summary.json')
    with open(report_path, 'w', encoding='utf-8') as fp:
        import json
        json.dump(report, fp, indent=2)

    markdown_lines = [
        '# Flight Price EDA Summary',
        '',
        f'Dataset version: {report["dataset_version"]}',
        f'Rows: {report["rows"]}',
        f'Columns: {len(report["columns"]) }',
        '',
        '## Price statistics',
        f'- Mean: ₹{report["price"]["mean"]:.2f}',
        f'- Median: ₹{report["price"]["median"]:.2f}',
        f'- Min: ₹{report["price"]["min"]:.2f}',
        f'- Max: ₹{report["price"]["max"]:.2f}',
        f'- Std Dev: ₹{report["price"]["std"]:.2f}',
        '',
        '## Missing values',
    ]
    for col, missing in report['missing_values'].items():
        markdown_lines.append(f'- {col}: {missing}')
    markdown_lines.extend(['', '## Unique values',])
    for col, unique in report['unique_values'].items():
        markdown_lines.append(f'- {col}: {unique}')
    markdown_lines.append('')
    markdown_lines.append('## Report artifacts')
    markdown_lines.append('- `eda_summary.json`')
    markdown_lines.append('- `eda_summary.md`')
    markdown_lines.append('- `eda_summary.pdf`')

    md_path = os.path.join(_REPORT_DIR, 'eda_summary.md')
    with open(md_path, 'w', encoding='utf-8') as md_fp:
        md_fp.write('\n'.join(markdown_lines))

    pdf_path = os.path.join(_REPORT_DIR, 'eda_summary.pdf')
    with PdfPages(pdf_path) as pdf:
        lines = [
            'Flight Price EDA Summary',
            '',
            f"Generated: {report['generated_at']}",
            f"Dataset version: {report['dataset_version']}",
            f"Rows: {report['rows']}",
            f"Columns: {len(report['columns'])}",
            '',
            'Price summary:',
            f"Mean: ₹{report['price']['mean']:.2f}",
            f"Median: ₹{report['price']['median']:.2f}",
            f"Min: ₹{report['price']['min']:.2f}",
            f"Max: ₹{report['price']['max']:.2f}",
            f"Std Dev: ₹{report['price']['std']:.2f}",
            '',
            'Missing values:',
        ]
        lines.extend([f"{col}: {missing}" for col, missing in report['missing_values'].items()])
        fig = plt.figure(figsize=(11, 8.5))
        fig.patch.set_facecolor('white')
        for index, line in enumerate(lines):
            fig.text(0.05, 0.95 - index * 0.03, line, fontsize=10, family='sans-serif')
        pdf.savefig(fig)
        plt.close(fig)

    return report_path


def _save_feature_engineering_report(feature_cols, encoders, row_count):
    report = {
        'generated_at': datetime.utcnow().isoformat(),
        'dataset_version': _get_dataset_version(),
        'feature_count': len(feature_cols),
        'feature_columns': feature_cols,
        'encoder_details': {key: list(value.classes_) for key, value in encoders.items()},
        'rows_after_processing': row_count,
    }
    report_path = os.path.join(_REPORT_DIR, 'feature_engineering.json')
    with open(report_path, 'w', encoding='utf-8') as fp:
        import json
        json.dump(report, fp, indent=2)

    markdown_lines = [
        '# Feature Engineering Summary',
        '',
        f'Dataset version: {report["dataset_version"]}',
        f'Rows after processing: {report["rows_after_processing"]}',
        f'Feature count: {report["feature_count"]}',
        '',
        '## Feature columns',
    ]
    for col in feature_cols:
        markdown_lines.append(f'- {col}')
    markdown_lines.extend(['', '## Encoded categorical features'])
    for key, classes in report['encoder_details'].items():
        markdown_lines.append(f'- {key}: {len(classes)} classes')
    markdown_lines.extend(['', '## Report artifacts', '- `feature_engineering.json`', '- `feature_engineering.md`', '- `feature_engineering.pdf`'])
    md_path = os.path.join(_REPORT_DIR, 'feature_engineering.md')
    with open(md_path, 'w', encoding='utf-8') as md_fp:
        md_fp.write('\n'.join(markdown_lines))

    pdf_path = os.path.join(_REPORT_DIR, 'feature_engineering.pdf')
    with PdfPages(pdf_path) as pdf:
        lines = [
            'Feature Engineering Summary',
            '',
            f"Generated: {report['generated_at']}",
            '',
            f"Rows after processing: {report['rows_after_processing']}",
            f"Feature count: {report['feature_count']}",
            '',
            'Encoded categorical features:',
        ]
        for key, classes in report['encoder_details'].items():
            lines.append(f"{key}: {len(classes)} classes")
        fig = plt.figure(figsize=(11, 8.5))
        fig.patch.set_facecolor('white')
        for index, line in enumerate(lines):
            fig.text(0.05, 0.95 - index * 0.03, line, fontsize=10, family='sans-serif')
        pdf.savefig(fig)
        plt.close(fig)

    return report_path


def _save_report(best_model, candidate_models, feature_cols, row_count, training_time_seconds=0.0):
    report = {
        'rows': row_count,
        'features': feature_cols,
        'models_evaluated': candidate_models,
        'best_model': best_model,
        'notes': 'Models evaluated using an 80/20 train/test split. The production model is the candidate with the lowest RMSE.',
        'dataset_version': _get_dataset_version(),
        'training_time_seconds': training_time_seconds,
        'generated_at': datetime.utcnow().isoformat(),
    }
    report_path = os.path.join(_REPORT_DIR, 'model_comparison.json')
    with open(report_path, 'w', encoding='utf-8') as fp:
        import json
        json.dump(report, fp, indent=2)

    markdown_lines = [
        '# Flight Price Model Comparison Report',
        '',
        f'Dataset version: {report["dataset_version"]}',
        f'Training date: {report["generated_at"]}',
        f'Rows: {report["rows"]}',
        f'Feature count: {len(feature_cols)}',
        f'Training time: {report["training_time_seconds"]:.2f} seconds',
        '',
        '## Models evaluated',
    ]
    for entry in candidate_models:
        r2_value = entry.get('r2')
        md_line = f'- {entry["name"]} ({entry.get("model_version", "N/A")}): RMSE={entry["rmse"]:.2f}, MAE={entry["mae"]:.2f}'
        if r2_value is not None:
            md_line += f', R2={r2_value:.4f}'
        markdown_lines.append(md_line)
    markdown_lines += [
        '',
        '## Best model',
        f'- {best_model["name"]} ({best_model.get("model_version", "N/A")}): RMSE={best_model["rmse"]:.2f}, MAE={best_model["mae"]:.2f}, R2={best_model.get("r2", 0.0):.4f}',
        '',
        '## Notes',
        report['notes'],
        '',
        '## Report artifacts',
        '- `model_comparison.json`',
        '- `model_comparison.md`',
        '- `model_comparison.pdf`',
    ]
    with open(os.path.join(_REPORT_DIR, 'model_comparison.md'), 'w', encoding='utf-8') as md_fp:
        md_fp.write('\n'.join(markdown_lines))

    _save_pdf_report(report, candidate_models, best_model)
    return report_path


def _save_metadata(best_model_name, encoders, scaler, feature_cols, candidate_models, model_path, training_time_seconds):
    joblib.dump(scaler, _SCALER_PATH)
    best_candidate = next((item for item in candidate_models if item['model_path'] == model_path), candidate_models[0] if candidate_models else {})
    metadata = {
        'encoders': encoders,
        'feature_cols': feature_cols,
        'best_model': best_model_name,
        'best_model_version': best_candidate.get('model_version', ''),
        'best_model_hyperparameters': best_candidate.get('hyperparameters', {}),
        'best_model_metrics': {
            'rmse': best_candidate.get('rmse'),
            'mae': best_candidate.get('mae'),
            'r2': best_candidate.get('r2'),
        },
        'candidate_models': candidate_models,
        'training_date': datetime.utcnow().isoformat(),
        'training_date_readable': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        'model_version': os.path.basename(model_path).replace('.joblib', ''),
        'model_path': model_path,
        'dataset_version': _get_dataset_version(),
        'training_time_seconds': training_time_seconds,
    }
    # Preserve legacy encoder names for backward compatibility
    metadata.update({f'le_{key.lower()}': value for key, value in encoders.items()})
    joblib.dump(metadata, _META_PATH)


def train_models():
    _require_ml_runtime()
    df = load_dataset()
    frame = prepare_feature_frame(df.copy())
    frame['Price'] = df['Price'].astype(float)

    feature_frame = frame.drop(columns=['Price'])
    feature_frame, encoders = _encode_features(feature_frame)
    feature_cols = list(feature_frame.columns)

    X = feature_frame.values.astype(float)
    y = frame['Price'].values.astype(float)

    scaler = MinMaxScaler()
    Xs = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(Xs, y, test_size=0.2, random_state=42)
    candidates = []
    start_time = time.time()

    for name, model in _supported_models().items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
        mae = float(mean_absolute_error(y_test, preds))
        r2 = float(r2_score(y_test, preds))
        version = _next_model_version(name)
        normalized_name = _normalize_model_name(name)
        model_filename = f"v{version}_{normalized_name}.joblib"
        model_path = os.path.join(_ARTIFACT_DIR, model_filename)
        joblib.dump(model, model_path)
        candidates.append({
            'name': name,
            'model_version': f'v{version}',
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'hyperparameters': model.get_params() if hasattr(model, 'get_params') else {},
            'model_path': model_path,
        })

    if not candidates:
        raise RuntimeError('No supported regression models are available in this environment.')

    best = min(candidates, key=lambda item: item['rmse'])
    best_model = joblib.load(best['model_path'])
    joblib.dump(best_model, _PRODUCTION_MODEL_PATH)
    joblib.dump(best_model, _BEST_MODEL_PATH)
    training_time_seconds = time.time() - start_time
    _save_metadata(best['name'], encoders, scaler, feature_cols, candidates, best['model_path'], training_time_seconds)
    _save_report(best, candidates, feature_cols, len(frame), training_time_seconds)
    _save_feature_engineering_report(feature_cols, encoders, len(frame))
    _save_eda_report(df)

    return {
        'best': best,
        'production_model_path': _PRODUCTION_MODEL_PATH,
        'candidate_models': candidates,
        'model_path': best['model_path'],
        'training_time_seconds': training_time_seconds,
    }


def train_pipeline():
    summary = train_models()
    return {
        'model_path': summary['model_path'],
        'rmse': summary['best']['rmse'],
        'mae': summary['best']['mae'],
        'best_model': summary['best']['name'],
        'candidate_models': summary['candidate_models'],
        'training_time_seconds': summary.get('training_time_seconds', 0.0),
    }


def load_model():
    if not os.path.exists(_PRODUCTION_MODEL_PATH) or not os.path.exists(_SCALER_PATH) or not os.path.exists(_META_PATH):
        return None, None, None
    model = joblib.load(_PRODUCTION_MODEL_PATH)
    metadata = joblib.load(_META_PATH)
    scaler = joblib.load(_SCALER_PATH)
    return model, metadata, scaler


def predict_price(airline, source, dest, dd, mm, yy, stops=None, travel_class=None):
    df = load_dataset()
    filtered = df.copy()
    if airline:
        filtered = filtered[filtered['Airline'].astype(str).str.lower() == str(airline).lower()]
    if source:
        filtered = filtered[filtered['Source'].astype(str).str.lower() == str(source).lower()]
    if dest:
        filtered = filtered[filtered['Destination'].astype(str).str.lower() == str(dest).lower()]
    general_price = round(float(filtered['Price'].mean()) if not filtered.empty else float(df['Price'].mean()), 2)

    stop_multiplier = 1.0
    if str(stops or '').strip().lower() in {'non-stop', 'non stop', 'nonstop'}:
        stop_multiplier = 0.94
    elif str(stops or '').strip().lower() in {'1 stop', '1-stop', '1', 'one stop'}:
        stop_multiplier = 1.05
    elif str(stops or '').strip().lower() in {'2 stops', '2-stop', '2'}:
        stop_multiplier = 1.12
    elif str(stops or '').strip().lower() in {'3+ stops', '3 stops', '3 stop'}:
        stop_multiplier = 1.18

    class_multiplier = 1.0
    if str(travel_class or '').strip().lower() in {'business class', 'business'}:
        class_multiplier = 1.18
    elif str(travel_class or '').strip().lower() in {'normal class', 'economy', 'standard'}:
        class_multiplier = 0.97

    airline_base = general_price
    if airline:
        airline_filtered = df[df['Airline'].astype(str).str.lower() == str(airline).lower()]
        if not airline_filtered.empty:
            airline_base = round(float(airline_filtered['Price'].mean()), 2)

    prediction = round(general_price * 0.92 + airline_base * 0.08 * stop_multiplier * class_multiplier, 2)

    try:
        _require_ml_runtime()
        model, metadata, scaler = load_model()
        if model is None or metadata is None or scaler is None:
            train_pipeline()
            model, metadata, scaler = load_model()

        if model is None or metadata is None or scaler is None:
            raise RuntimeError('Unable to load or train the production model.')

        inp = _build_input_row(metadata, scaler, airline, source, dest, dd, mm, yy)
        pred = float(model.predict(inp)[0])
        return {
            'prediction': round(pred, 2),
            'general_price': general_price,
            'selected_model': metadata.get('best_model', 'production_model'),
            'model_version': metadata.get('model_version', ''),
        }
    except Exception:
        return {
            'prediction': prediction,
            'general_price': general_price,
            'selected_model': 'fallback_estimate',
            'model_version': 'fallback',
        }
