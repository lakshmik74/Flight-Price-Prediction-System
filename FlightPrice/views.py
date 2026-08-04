from django.shortcuts import render, redirect
from datetime import datetime
from django.template import RequestContext
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.db.models import Avg, Count
from .models import Signup as SignupModel, PredictionHistory, RetrainingHistory
from .utils import ensure_signup_table
import re
import numpy as np
from functools import wraps
from pathlib import Path
import math

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend to prevent GUI issues
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
except Exception:
    matplotlib = None
    plt = None
    PdfPages = None

import pandas as pd
import numpy as np

try:
    from sklearn.preprocessing import MinMaxScaler, LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.tree import DecisionTreeRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
except Exception as sklearn_import_error:
    MinMaxScaler = None
    LabelEncoder = None
    train_test_split = None
    RandomForestRegressor = None
    GradientBoostingRegressor = None
    LinearRegression = None
    DecisionTreeRegressor = None
    mean_absolute_error = None
    mean_squared_error = None
    r2_score = None
    _SKLEARN_IMPORT_ERROR = sklearn_import_error
else:
    _SKLEARN_IMPORT_ERROR = None

try:
    import seaborn as sns
except Exception:
    sns = None

import io
import base64
import json
import os
import difflib
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from .ml.model import predict_price, train_pipeline, load_model, _get_dataset_version
except Exception as ml_import_error:
    predict_price = None
    train_pipeline = None
    load_model = None
    _get_dataset_version = None
    _ML_IMPORT_ERROR = ml_import_error
else:
    _ML_IMPORT_ERROR = None

from .ml.data import load_dataset

uname = None
le1 = None
le2 = None
le3 = None
scaler = None
rf = None
dataset = None
X = None
Y = None
feature_columns = None


def _safe_messages_error(request, text):
    try:
        messages.error(request, text)
    except Exception:
        pass


def _safe_messages_success(request, text):
    try:
        messages.success(request, text)
    except Exception:
        pass


def _safe_messages_info(request, text):
    try:
        messages.info(request, text)
    except Exception:
        pass


def _safe_messages_warning(request, text):
    try:
        messages.warning(request, text)
    except Exception:
        pass

def require_login(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request, 'session') or request.session is None:
            request.session = {}
        if not request.session.get('username'):
            try:
                messages.warning(request, 'Please log in to access this page.')
            except Exception:
                pass
            return redirect('/UserLogin')
        return view_func(request, *args, **kwargs)
    return _wrapped_view



def _get_api_status():
    api_url = os.getenv('FLIGHT_API_URL')
    api_key = os.getenv('FLIGHT_API_KEY') or os.getenv('FLIGHT_API_TOKEN')
    if not api_url or not api_key:
        return {'status': 'Not configured', 'message': 'Live flight price API is not configured.'}
    return {'status': 'Configured', 'message': 'Live flight price API credentials are configured.'}


def _ml_runtime_error_message():
    if _ML_IMPORT_ERROR is not None:
        return str(_ML_IMPORT_ERROR)
    return 'The ML runtime is unavailable in this environment.'


def UserLogin(request):
    if request.method == 'GET':
       if request.session.get('username'):
           return redirect('/Dashboard')
       return render(request, 'UserLogin.html', {})

def index(request):
    if request.method == 'GET':
       return render(request, 'index.html', {})

def Signup(request):
    if request.method == 'GET':
       return render(request, 'Signup.html', {})

def SignupAction(request):
    if request.method == 'POST':
        ensure_signup_table()
        username = request.POST.get('t1', False)
        password = request.POST.get('t2', False)
        contact = request.POST.get('t3', False)
        email = request.POST.get('t4', False)
        address = request.POST.get('t5', False)

        password_pattern = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$')
        if not password_pattern.match(str(password)):
            messages.warning(request, 'Password must be at least 8 characters and include uppercase, lowercase, number, and special character.')
            return render(request, 'Signup.html', {})

        try:
            if SignupModel.objects.filter(username=username).exists():
                messages.warning(request, 'Username already exists. Please choose a different username.')
                return render(request, 'Signup.html', {})
            SignupModel.objects.create(
                username=username,
                password=password,
                contact_no=contact,
                email_id=email,
                address=address
            )
            messages.success(request, 'Signup completed successfully. Please log in to continue.')
            return redirect('/UserLogin')
        except Exception as e:
            messages.error(request, f'Error during signup: {str(e)}')
            return render(request, 'Signup.html', {})

def UserLoginAction(request):
    if request.method == 'POST':
        username = request.POST.get('username', False)
        password = request.POST.get('password', False)

        try:
            SignupModel.objects.get(username=username, password=password)
            request.session['username'] = username
            request.session.modified = True
            messages.success(request, 'Logged in successfully.')
            return redirect('/Dashboard')
        except SignupModel.DoesNotExist:
            messages.error(request, 'Invalid login details. Please try again.')
            return render(request, 'UserLogin.html', {})

def ForgotPassword(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()

        if not username or not email:
            messages.warning(request, 'Please enter both username and email address.')
            return render(request, 'ForgotPassword.html', {})

        if SignupModel.objects.filter(username=username, email_id=email).exists():
            messages.success(request, 'If the account exists, a password reset link has been sent to your email.')
        else:
            messages.error(request, 'Could not find an account with that username and email.')
        return render(request, 'ForgotPassword.html', {})

    return render(request, 'ForgotPassword.html', {})


def Logout(request):
    request.session.flush()
    messages.info(request, 'You have been logged out successfully.')
    return redirect('/UserLogin')


@require_login
def Dashboard(request):
    username = request.session.get('username')
    report = _load_model_report()
    report_available = report is not None
    # report may contain best_model as dict or string depending on generator
    if report_available:
        best = report.get('best_model', {})
        if isinstance(best, dict):
            best_model = best.get('name', str(best))
            best_rmse = best.get('rmse')
            best_mae = best.get('mae')
        else:
            best_model = str(best)
            best_rmse = None
            best_mae = None
        feature_count = len(report.get('features', [])) if report.get('features') else 0
        total_rows = report.get('rows', 0)
        top_models = report.get('models_evaluated') or report.get('models') or []
        top_models = top_models[:3]
    else:
        best_model = 'Not trained yet'
        best_rmse = None
        best_mae = None
        feature_count = 0
        total_rows = 0
        top_models = []

    context = {
        'username': username,
        'report_available': report_available,
        'best_model': best_model,
        'feature_count': feature_count,
        'total_rows': total_rows,
        'best_rmse': best_rmse,
        'best_mae': best_mae,
        'top_models': top_models,
    }
    return render(request, 'Dashboard.html', context)


@require_login
def AdminPanel(request):
    username = request.session.get('username')
    report = _load_model_report()
    models_dir = Path(__file__).resolve().parents[2] / 'models'
    reports_dir = _get_reports_dir()
    artifact_files = []

    if models_dir.exists():
        for model_file in sorted(models_dir.glob('*.joblib')):
            artifact_files.append({
                'name': model_file.name,
                'type': 'Model',
                'size_kb': round(model_file.stat().st_size / 1024, 2),
                'modified_at': datetime.fromtimestamp(model_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            })

    report_path = reports_dir / 'model_comparison.json'
    report_present = report is not None and report_path.exists()
    report_modified_at = None
    report_excerpt = None
    best_model_name = 'Not trained yet'
    top_models = []

    if reports_dir.exists():
        for report_file in sorted(reports_dir.glob('*')):
            if report_file.suffix.lower() in {'.json', '.md', '.pdf'}:
                artifact_files.append({
                    'name': report_file.name,
                    'type': 'Report',
                    'size_kb': round(report_file.stat().st_size / 1024, 2),
                    'modified_at': datetime.fromtimestamp(report_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                })

    artifact_count = len(artifact_files)

    if report_present:
        report_modified_at = datetime.fromtimestamp(report_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        best_model_name = report.get('best_model', best_model_name)
        report_excerpt = report.get('notes', '')
        if isinstance(report.get('models_evaluated'), list):
            top_models = report['models_evaluated'][:3]
        elif isinstance(report.get('models'), list):
            top_models = report['models'][:3]

    total_predictions = PredictionHistory.objects.count()
    avg_error_value = PredictionHistory.objects.aggregate(avg_err=Avg('percentage_error'))['avg_err']
    avg_prediction_error = round(avg_error_value, 2) if avg_error_value is not None else None
    last_training = RetrainingHistory.objects.order_by('-training_date').first()
    if last_training:
        production_model_version = last_training.model_version
        dataset_version = last_training.dataset_version
        last_training_date = last_training.training_date.strftime('%Y-%m-%d %H:%M:%S')
        training_time_seconds = last_training.training_time_seconds or 0.0
        production_model_name = last_training.model_name
    else:
        production_model_version = 'N/A'
        dataset_version = 'N/A'
        last_training_date = 'N/A'
        training_time_seconds = 0.0
        production_model_name = report.get('best_model', 'N/A') if report else 'N/A'

    api_status = _get_api_status()
    if avg_prediction_error is None:
        model_health = 'No predictions yet'
    elif avg_prediction_error <= 5:
        model_health = 'Excellent'
    elif avg_prediction_error <= 10:
        model_health = 'Good'
    elif avg_prediction_error <= 20:
        model_health = 'Moderate'
    else:
        model_health = 'Needs review'

    context = {
        'username': username,
        'report_available': report_present,
        'best_model': best_model_name,
        'row_count': report.get('rows', 0) if report else 0,
        'artifact_files': artifact_files,
        'model_dir': str(models_dir),
        'artifact_count': artifact_count,
        'report_path': str(report_path) if report_present else 'Not available',
        'report_modified_at': report_modified_at,
        'report_excerpt': report_excerpt,
        'top_models': top_models,
        'total_predictions': total_predictions,
        'avg_prediction_error': round(avg_prediction_error, 2) if avg_prediction_error is not None else None,
        'production_model_version': production_model_version,
        'dataset_version': dataset_version,
        'last_training_date': last_training_date,
        'training_time_seconds': round(training_time_seconds, 2),
        'production_model_name': production_model_name,
        'api_status': api_status,
        'model_health': model_health,
    }
    return render(request, 'AdminPanel.html', context)


@require_login
def AdminDownloadArtifact(request, artifact_name):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', artifact_name):
        return HttpResponse('Invalid artifact name.', status=400)

    models_dir = Path(__file__).resolve().parents[2] / 'models'
    reports_dir = _get_reports_dir()
    candidate_path = None

    for directory in [models_dir, reports_dir]:
        path = (directory / artifact_name).resolve()
        if directory in path.parents or path == directory and os.path.exists(path):
            if path.exists() and path.is_file():
                candidate_path = path
                break

    if candidate_path is None:
        return HttpResponse('Artifact not found.', status=404)

    try:
        response = FileResponse(candidate_path.open('rb'), as_attachment=True, filename=candidate_path.name, content_type='application/octet-stream')
        return response
    except Exception as e:
        messages.error(request, f'Unable to download artifact: {e}')
        return redirect('/AdminPanel')


@require_login
def AdminRetrain(request):
    if request.method != 'POST':
        return redirect('/AdminPanel')
    models_dir = Path(__file__).resolve().parents[2] / 'models'
    archive_dir = models_dir / 'archive'
    archive_dir.mkdir(parents=True, exist_ok=True)

    prev_meta_path = models_dir / 'model_metadata.joblib'
    prev_prod = models_dir / 'production_model.joblib'
    prev_rmse = None
    if prev_meta_path.exists():
        try:
            import joblib as _joblib
            prev_meta = _joblib.load(str(prev_meta_path))
            prev_rmse = prev_meta.get('best_model_metrics', {}).get('rmse')
        except Exception:
            prev_rmse = None

    # Archive previous production and metadata to allow rollback
    try:
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        if prev_prod.exists():
            archived_prod = archive_dir / f'production_{timestamp}.joblib'
            with prev_prod.open('rb') as s, archived_prod.open('wb') as d:
                d.write(s.read())
        if prev_meta_path.exists():
            archived_meta = archive_dir / f'model_metadata_{timestamp}.joblib'
            with prev_meta_path.open('rb') as s, archived_meta.open('wb') as d:
                d.write(s.read())
    except Exception as e:
        messages.warning(request, f'Failed to archive previous production model: {e}')

    try:
        summary = train_pipeline()
        new_rmse = summary.get('rmse')

        # Decide whether to keep new production: if previous RMSE exists and new is worse, restore previous
        deploy_new = True
        if prev_rmse is not None and new_rmse is not None:
            try:
                deploy_new = float(new_rmse) < float(prev_rmse)
            except Exception:
                deploy_new = True

        if not deploy_new:
            # restore previous production model and metadata
            try:
                # find the latest archived files
                archived_prods = sorted(archive_dir.glob('production_*.joblib'), reverse=True)
                archived_metas = sorted(archive_dir.glob('model_metadata_*.joblib'), reverse=True)
                if archived_prods:
                    with archived_prods[0].open('rb') as s, prev_prod.open('wb') as d:
                        d.write(s.read())
                if archived_metas:
                    with archived_metas[0].open('rb') as s, prev_meta_path.open('wb') as d:
                        d.write(s.read())
                messages.info(request, 'New model was not better; restored previous production model.')
            except Exception as e:
                messages.error(request, f'Failed to restore previous production: {e}')

            # Record retraining history but mark not promoted to production
            import joblib as _joblib
            model, metadata, _ = load_model()
            RetrainingHistory.objects.create(
                model_name=summary.get('best_model', 'unknown'),
                model_version=summary.get('best_model', ''),
                dataset_version=metadata.get('dataset_version', '') if metadata else '',
                rmse=new_rmse or 0.0,
                mae=summary.get('mae', 0.0),
                training_time_seconds=summary.get('training_time_seconds', 0.0),
                model_path=summary.get('model_path', ''),
                is_production=False,
            )
            messages.success(request, f"Retraining complete. New model: {summary.get('best_model')} (RMSE: {new_rmse:.2f}) — not promoted.")
            return redirect('/AdminPanel')

        # If we get here, new model is better and train_pipeline already deployed it
        model, metadata, _ = load_model()
        RetrainingHistory.objects.create(
            model_name=summary.get('best_model', 'unknown'),
            model_version=metadata.get('model_version', '') if metadata else '',
            dataset_version=metadata.get('dataset_version', '') if metadata else '',
            rmse=new_rmse or 0.0,
            mae=summary.get('mae', 0.0),
            training_time_seconds=summary.get('training_time_seconds', 0.0),
            model_path=summary.get('model_path', ''),
            is_production=True,
        )
        messages.success(request, f"Retraining complete. Best model: {summary.get('best_model')} (RMSE: {new_rmse:.2f}) promoted to production.")
    except Exception as e:
        messages.error(request, f"Retraining failed: {e}")
    return redirect('/AdminPanel')


@require_login
def AdminClearArtifacts(request):
    if request.method != 'POST':
        return redirect('/AdminPanel')

    models_dir = Path(__file__).resolve().parents[2] / 'models'
    reports_dir = _get_reports_dir()
    deleted_files = []
    failed_files = []

    for directory in [models_dir, reports_dir]:
        if directory.exists():
            for item in directory.glob('*'):
                if item.suffix in {'.joblib', '.json', '.md'}:
                    try:
                        item.unlink()
                        deleted_files.append(item.name)
                    except Exception as e:
                        failed_files.append(f"{item.name}: {e}")

    if deleted_files:
        messages.success(request, f"Deleted artifacts: {', '.join(deleted_files)}")
    if failed_files:
        messages.error(request, f"Failed to delete: {', '.join(failed_files)}")
    if not deleted_files and not failed_files:
        messages.info(request, 'No artifacts were found to delete.')

    return redirect('/AdminPanel')


@require_login
def DatasetCollection(request):
    if request.method == 'GET':
        global dataset
        dataset = load_dataset()

        query = (request.GET.get('q') or '').strip()
        page = request.GET.get('page', '1')
        try:
            page = int(page)
        except Exception:
            page = 1
        page = max(1, page)
        page_size = 25

        filtered = dataset.copy()
        if query:
            filtered = filtered[
                filtered.astype(str).apply(lambda column: column.str.contains(query, case=False, na=False)).any(axis=1)
            ].reset_index(drop=True)

        if request.GET.get('download') == '1':
            response = HttpResponse(filtered.to_csv(index=False), content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="flightprice_dataset.csv"'
            return response

        total_rows = len(filtered)
        total_pages = max(1, math.ceil(total_rows / page_size)) if total_rows else 1
        page = min(page, total_pages)
        start = (page - 1) * page_size
        end = start + page_size
        page_rows = filtered.iloc[start:end]

        rows = page_rows.values.tolist()
        columns = filtered.columns.tolist()
        record_count = len(dataset)
        showing_count = len(rows)

        img_b64 = None
        if sns is not None and plt is not None:
            try:
                temp = dataset[['Airline', 'Price', 'Source', 'Destination']].copy()
                sns.catplot(x='Airline', y='Price', hue='Source', data=temp, kind='point')
                plt.title('Price Comparison between Different Airlines')
                plt.xticks(rotation=90)
                plt.tight_layout()
                buf = io.BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight')
                plt.close()
                img_b64 = base64.b64encode(buf.getvalue()).decode()
            except Exception:
                img_b64 = None

        context = {
            'columns': columns,
            'rows': rows,
            'record_count': record_count,
            'showing_count': showing_count,
            'query': query,
            'page': page,
            'page_size': page_size,
            'page_count': total_pages,
            'total_rows': total_rows,
            'graph1b64': img_b64,
        }
        return render(request, 'DatasetCollection.html', context)


@require_login
def AdminCleanRetraining(request):
    """Remove RetrainingHistory DB entries whose model artifact files are missing.

    This is a safe admin action that helps clean up audit records when artifacts
    have been removed from disk. It reports counts via Django messages and
    redirects back to the AdminPanel.
    """
    if request.method != 'POST':
        return redirect('/AdminPanel')

    # Delegate to the reusable helper so this logic can be scheduled
    models_dir = None
    deleted, failed = _clean_retraining_history(models_dir=models_dir)

    if deleted:
        messages.success(request, f"Removed {deleted} retraining history entr{'y' if deleted==1 else 'ies'} with missing artifacts.")
    if failed:
        messages.error(request, f"Failed to remove some entries: {', '.join(failed)}")
    if not deleted and not failed:
        messages.info(request, 'No retraining history entries required cleaning.')

    return redirect('/AdminPanel')


@require_login
def AdminResetPredictionHistory(request):
    if request.method != 'POST':
        return redirect('/AdminPanel')

    try:
        deleted, _ = PredictionHistory.objects.all().delete()
        messages.success(request, f'Reset prediction history. Deleted {deleted} prediction records.')
    except Exception as e:
        messages.error(request, f'Failed to reset prediction history: {e}')

    return redirect('/AdminPanel')


def _clean_retraining_history(models_dir: Path | None = None):
    """Helper used by views and management command.

    Returns a tuple (deleted_count, list_of_failures).
    """
    if models_dir is None:
        models_dir = Path(__file__).resolve().parents[2] / 'models'

    deleted = 0
    failed = []

    # Iterate over DB rows and remove those whose artifact file is missing
    for run in RetrainingHistory.objects.all():
        artifact = models_dir / f"{run.model_version}.joblib"
        if not artifact.exists():
            try:
                run.delete()
                deleted += 1
            except Exception as e:
                failed.append(f"{run.model_version}: {e}")

    return deleted, failed


@require_login
def AdminUploadDataset(request):
    if request.method != 'POST':
        return redirect('/AdminPanel')

    upload = request.FILES.get('dataset')
    if not upload:
        messages.error(request, 'No dataset file uploaded.')
        return redirect('/AdminPanel')

    try:
        datasets_dir = Path(__file__).resolve().parents[2] / 'Dataset'
        datasets_dir.mkdir(parents=True, exist_ok=True)
        target = datasets_dir / 'FlightPrice.csv'
        with target.open('wb') as f:
            for chunk in upload.chunks():
                f.write(chunk)
        messages.success(request, 'Uploaded dataset saved to Dataset/FlightPrice.csv')
    except Exception as e:
        messages.error(request, f'Failed to save uploaded dataset: {e}')

    return redirect('/AdminPanel')

@require_login
def DatasetCleaning(request):
    if request.method == 'GET':
        global dataset, le1, le2, le3, scaler, X, Y
        dataset['Date_of_Journey'] = pd.to_datetime(dataset['Date_of_Journey'])
        dataset['year'] = dataset['Date_of_Journey'].dt.year
        dataset['month'] = dataset['Date_of_Journey'].dt.month
        dataset['day'] = dataset['Date_of_Journey'].dt.day
        Y = np.asarray(dataset['Price']).ravel()
        dataset.drop(['Date_of_Journey', 'Dep_Time', 'Arrival_Time', 'Duration', 'Price'], axis = 1,inplace=True)
        le1 = LabelEncoder()
        le2 = LabelEncoder()
        le3 = LabelEncoder()
        dataset['Airline'] = pd.Series(le1.fit_transform(dataset['Airline'].astype(str)))#encode all str columns to numeric
        dataset['Source'] = pd.Series(le2.fit_transform(dataset['Source'].astype(str)))#encode all str columns to numeric
        dataset['Destination'] = pd.Series(le3.fit_transform(dataset['Destination'].astype(str)))#encode all str columns to numeric
        scaler = MinMaxScaler()
        columns = dataset.columns
        X = dataset.values
        X = scaler.fit_transform(X)
        
        # Create modern Bootstrap table with proper styling
        output = '''
        <div class="table-responsive">
            <table class="table table-striped table-hover table-bordered">
                <thead>
                    <tr>
        '''
        
        for i in range(len(columns)):
            output += f'<th scope="col">{columns[i]}</th>'
        
        output += '''
                    </tr>
                </thead>
                <tbody>
        '''
        
        # Show only first 50 rows to avoid overwhelming the page
        for i in range(min(50, len(X))):
            output += '<tr>'
            for j in range(len(X[i])):
                output += f'<td>{str(round(X[i,j], 4))}</td>'
            output += '</tr>'
        
        output += '''
                </tbody>
            </table>
        </div>
        '''
        
        # Add summary information
        output += f'''
        <div class="alert alert-success mt-3">
            <strong>Data Cleaning Complete!</strong> Total {len(X)} records processed. Showing first 50 records.
        </div>
        '''
        
        context = {'data': output}
        return render(request, 'UserScreen.html', context)

@require_login
def TrainRF(request):
    if request.method == 'GET':
        global dataset, le1, le2, le3, scaler, X, Y, rf
        X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.2, random_state=0)
        rf = RandomForestRegressor()
        rf.fit(X, Y)
        predict = rf.predict(X_test)
        
        # Create modern Bootstrap table with proper styling
        output = '''
        <div class="table-responsive">
            <table class="table table-striped table-hover table-bordered">
                <thead>
                    <tr>
        '''
        output += '<th scope="col">True Test Price</th>'
        output += '<th scope="col">Random Forest Predicted Price</th>'
        output += '''
                    </tr>
                </thead>
                <tbody>
        '''

        labels = y_test[0:100]
        predict = predict[0:100]
        for i in range(len(labels)):
            output += f'<tr><td>{str(int(labels[i]))}</td>'
            output += f'<td>{str(int(predict[i]))}</td></tr>'
        
        output += '''
                </tbody>
            </table>
        </div>
        '''
        
        # Add model performance summary
        mse = np.mean((labels - predict) ** 2)
        rmse = np.sqrt(mse)
        output += f'''
        <div class="alert alert-info mt-3">
            <strong>Model Performance:</strong> RMSE = {rmse:.2f}
        </div>
        '''
        
        plt.plot(labels, color = 'red', label = 'True Test Price')
        plt.plot(predict, color = 'green', label = 'Random Forest Predicted Price')
        plt.title("Random Forest Flight Price Prediction Graph")
        plt.xlabel('Number of Days')
        plt.ylabel('Predicted Prices')
        plt.legend()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        img_b64 = base64.b64encode(buf.getvalue()).decode()
        
        context = {'data': output, 'graph1b64': img_b64}
        return render(request, 'UserScreen.html', context)


@require_login
def TrainML(request):
    if request.method == 'GET':
        try:
            summary = train_pipeline()
            context = {
                'best_model': summary.get('best_model', 'unknown'),
                'rmse': f"{summary.get('rmse', 0.0):.2f}",
                'mae': f"{summary.get('mae', 0.0):.2f}",
                'training_time': f"{summary.get('training_time_seconds', 0.0):.2f}",
                'candidate_models': [
                    {
                        'name': candidate.get('name', 'unknown'),
                        'rmse': f"{candidate.get('rmse', 0.0):.2f}",
                        'mae': f"{candidate.get('mae', 0.0):.2f}",
                        'r2': f"{candidate.get('r2', 0.0):.4f}",
                    }
                    for candidate in summary.get('candidate_models', [])
                ],
                'error_message': None,
            }
        except Exception as e:
            context = {
                'error_message': str(e),
                'best_model': None,
                'rmse': None,
                'mae': None,
                'training_time': None,
                'candidate_models': [],
            }
        return render(request, 'TrainML.html', context)


@require_login
def AdminPromoteArtifact(request, artifact_name):
    # Promote a chosen model artifact to production
    if request.method != 'POST':
        return redirect('/ModelMonitoring')

    if not re.fullmatch(r'[A-Za-z0-9_.-]+', artifact_name):
        messages.error(request, 'Invalid artifact name.')
        return redirect('/ModelMonitoring')

    models_dir = Path(__file__).resolve().parents[2] / 'models'
    candidate = models_dir / artifact_name
    if not candidate.exists() or not candidate.is_file():
        messages.error(request, f'Artifact {artifact_name} not found.')
        return redirect('/ModelMonitoring')

    try:
        prod_path = models_dir / 'production_model.joblib'
        # Overwrite production model
        with candidate.open('rb') as src, prod_path.open('wb') as dst:
            dst.write(src.read())

        # Update metadata to reflect promotion
        import joblib as _joblib
        meta = {
            'model_version': candidate.name.replace('.joblib', ''),
            'model_path': str(prod_path),
            'dataset_version': _get_dataset_version(),
            'training_date': datetime.utcnow().isoformat(),
            'training_date_readable': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        }
        _joblib.dump(meta, Path(models_dir / 'model_metadata.joblib'))

        # Record in RetrainingHistory for audit
        RetrainingHistory.objects.create(
            model_name=candidate.stem,
            model_version=candidate.stem,
            dataset_version=meta.get('dataset_version', ''),
            rmse=0.0,
            mae=0.0,
            training_time_seconds=0.0,
            model_path=str(prod_path),
            is_production=True,
        )

        messages.success(request, f'Promoted {artifact_name} to production.')
    except Exception as e:
        messages.error(request, f'Promotion failed: {e}')

    return redirect('/ModelMonitoring')


@require_login
def AdminRollbackArtifact(request, artifact_name):
    # Rollback production to a previous artifact
    if request.method != 'POST':
        return redirect('/ModelMonitoring')

    if not re.fullmatch(r'[A-Za-z0-9_.-]+', artifact_name):
        messages.error(request, 'Invalid artifact name.')
        return redirect('/ModelMonitoring')

    models_dir = Path(__file__).resolve().parents[2] / 'models'
    candidate = models_dir / artifact_name
    if not candidate.exists() or not candidate.is_file():
        messages.error(request, f'Artifact {artifact_name} not found for rollback.')
        return redirect('/ModelMonitoring')

    try:
        prod_path = models_dir / 'production_model.joblib'
        with candidate.open('rb') as src, prod_path.open('wb') as dst:
            dst.write(src.read())

        import joblib as _joblib
        meta = {
            'model_version': candidate.name.replace('.joblib', ''),
            'model_path': str(prod_path),
            'dataset_version': _get_dataset_version(),
            'training_date': datetime.utcnow().isoformat(),
            'training_date_readable': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'rolled_back': True,
        }
        _joblib.dump(meta, Path(models_dir / 'model_metadata.joblib'))

        RetrainingHistory.objects.create(
            model_name=candidate.stem,
            model_version=candidate.stem,
            dataset_version=meta.get('dataset_version', ''),
            rmse=0.0,
            mae=0.0,
            training_time_seconds=0.0,
            model_path=str(prod_path),
            is_production=True,
        )

        messages.success(request, f'Rolled back production to {artifact_name}.')
    except Exception as e:
        messages.error(request, f'Rollback failed: {e}')

    return redirect('/ModelMonitoring')


def _get_reports_dir():
    return Path(__file__).resolve().parents[2] / 'reports'


def _load_model_report():
    report_path = _get_reports_dir() / 'model_comparison.json'
    if not report_path.exists():
        return None
    import json
    with report_path.open('r', encoding='utf-8') as fp:
        return json.load(fp)


def _save_prediction_history_report():
    reports_dir = _get_reports_dir()
    reports_dir.mkdir(parents=True, exist_ok=True)

    total_predictions = PredictionHistory.objects.count()
    average_error = PredictionHistory.objects.aggregate(avg_error=Avg('percentage_error'))['avg_error'] or 0.0
    status_breakdown = list(PredictionHistory.objects.values('status').annotate(count=Count('id')).order_by('-count'))
    top_routes = list(
        PredictionHistory.objects.values('source', 'destination')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    report = {
        'generated_at': datetime.utcnow().isoformat(),
        'total_predictions': total_predictions,
        'average_percentage_error': round(float(average_error), 2),
        'status_breakdown': status_breakdown,
        'top_routes': top_routes,
        'latest_prediction': PredictionHistory.objects.order_by('-created_at').values('airline', 'source', 'destination', 'predicted_price', 'live_price', 'percentage_error', 'status', 'created_at').first() or {},
    }

    json_path = reports_dir / 'prediction_summary.json'
    md_path = reports_dir / 'prediction_summary.md'
    pdf_path = reports_dir / 'prediction_summary.pdf'

    with json_path.open('w', encoding='utf-8') as fp:
        import json
        json.dump(report, fp, indent=2)

    markdown_lines = [
        '# Prediction History Summary',
        '',
        f"Generated: {report['generated_at']}",
        f"Total predictions: {report['total_predictions']}",
        f"Average percentage error: {report['average_percentage_error']}%",
        '',
        '## Status breakdown',
    ]
    for entry in report['status_breakdown']:
        markdown_lines.append(f"- {entry['status']}: {entry['count']}")
    markdown_lines.extend(['', '## Top routes',])
    for entry in report['top_routes']:
        markdown_lines.append(f"- {entry['source']} → {entry['destination']}: {entry['count']} predictions")
    markdown_lines.extend(['', '## Latest prediction',])
    latest = report['latest_prediction']
    if latest:
        markdown_lines.extend([
            f"- Airline: {latest.get('airline', 'N/A')}",
            f"- Source: {latest.get('source', 'N/A')}",
            f"- Destination: {latest.get('destination', 'N/A')}",
            f"- Predicted price: ₹{latest.get('predicted_price', 0.0):.2f}",
            f"- Live price: ₹{latest.get('live_price', 0.0):.2f}",
            f"- Error: {latest.get('percentage_error', 0.0):.2f}%",
            f"- Status: {latest.get('status', 'N/A')}",
        ])
    else:
        markdown_lines.append('- No predictions recorded yet.')
    markdown_lines.extend(['', '## Report artifacts', '- `prediction_summary.json`', '- `prediction_summary.md`', '- `prediction_summary.pdf`'])

    md_path.write_text('\n'.join(markdown_lines), encoding='utf-8')

    if PdfPages is not None and plt is not None:
        with PdfPages(pdf_path) as pdf:
            lines = [
                'Prediction History Summary',
                '',
                f"Generated: {report['generated_at']}",
                f"Total predictions: {report['total_predictions']}",
                f"Average percentage error: {report['average_percentage_error']}%",
                '',
                'Status breakdown:',
            ]
            for entry in report['status_breakdown']:
                lines.append(f"{entry['status']}: {entry['count']}")
            lines.extend(['', 'Top routes:'])
            for entry in report['top_routes']:
                lines.append(f"{entry['source']} → {entry['destination']}: {entry['count']}")
            if latest:
                lines.extend(['', 'Latest prediction:'])
                lines.append(f"Airline: {latest.get('airline', 'N/A')}")
                lines.append(f"Source: {latest.get('source', 'N/A')}")
                lines.append(f"Destination: {latest.get('destination', 'N/A')}")
                lines.append(f"Predicted price: ₹{latest.get('predicted_price', 0.0):.2f}")
                lines.append(f"Live price: ₹{latest.get('live_price', 0.0):.2f}")
                lines.append(f"Error: {latest.get('percentage_error', 0.0):.2f}%")
                lines.append(f"Status: {latest.get('status', 'N/A')}")
            fig = plt.figure(figsize=(11, 8.5))
            fig.patch.set_facecolor('white')
            for idx, line in enumerate(lines):
                fig.text(0.05, 0.95 - idx * 0.03, line, fontsize=10, family='sans-serif')
            pdf.savefig(fig)
            plt.close(fig)

    return json_path


def _collect_artifacts():
    models_dir = Path(__file__).resolve().parents[2] / 'models'
    reports_dir = _get_reports_dir()
    artifact_files = []

    if models_dir.exists():
        for model_file in sorted(models_dir.glob('*.joblib')):
            artifact_files.append({
                'name': model_file.name,
                'type': 'Model',
                'size_kb': round(model_file.stat().st_size / 1024, 2),
                'modified_at': datetime.fromtimestamp(model_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            })

    if reports_dir.exists():
        for report_file in sorted(reports_dir.glob('*')):
            if report_file.suffix.lower() in {'.json', '.md', '.pdf'}:
                artifact_files.append({
                    'name': report_file.name,
                    'type': 'Report',
                    'size_kb': round(report_file.stat().st_size / 1024, 2),
                    'modified_at': datetime.fromtimestamp(report_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                })

    report_path = reports_dir / 'model_comparison.json'
    return artifact_files, models_dir, reports_dir, report_path


@require_login
def ModelReport(request):
    report = _load_model_report()
    if report is None:
        messages.warning(request, 'No model comparison report found. Train the model first.')
        return redirect('/TrainML')

    report_best = report.get('best_model', {})
    if isinstance(report_best, dict):
        best_model_name = report_best.get('name', 'Unknown')
        best_rmse = report_best.get('rmse')
        best_mae = report_best.get('mae')
        best_r2 = report_best.get('r2')
    else:
        best_model_name = str(report_best)
        best_rmse = None
        best_mae = None
        best_r2 = None

    context = {
        'best_model_name': best_model_name,
        'best_rmse': best_rmse,
        'best_mae': best_mae,
        'best_r2': best_r2,
        'models': report.get('models_evaluated', []),
        'total_rows': report.get('rows', 0),
        'feature_count': len(report.get('features', [])),
        'note': report.get('notes', ''),
    }
    return render(request, 'ModelReport.html', context)


@require_login
def ModelMonitoring(request):
    username = request.session.get('username')
    report = _load_model_report()
    artifact_files, models_dir, reports_dir, report_path = _collect_artifacts()
    production_model_path = models_dir / 'production_model.joblib'
    production_model_exists = production_model_path.exists()
    report_present = report is not None and report_path.exists()
    report_modified_at = None
    report_excerpt = ''
    top_models = []

    if report_present:
        report_modified_at = datetime.fromtimestamp(report_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        report_excerpt = report.get('notes', '')
        top_models = report.get('models_evaluated') or report.get('models') or []
        top_models = top_models[:3]

    total_predictions = PredictionHistory.objects.count()
    avg_error_value = PredictionHistory.objects.aggregate(avg_err=Avg('percentage_error'))['avg_err']
    avg_prediction_error = round(avg_error_value, 2) if avg_error_value is not None else None
    status_breakdown = list(PredictionHistory.objects.values('status').annotate(count=Count('status')).order_by('-count'))
    last_prediction = PredictionHistory.objects.order_by('-created_at').first()
    retraining_history = list(RetrainingHistory.objects.order_by('-training_date')[:10])
    retraining_history_items = []
    for run in retraining_history:
        candidate_artifact = models_dir / f"{run.model_version}.joblib"
        retraining_history_items.append({
            'training_date': run.training_date,
            'model_name': run.model_name,
            'model_version': run.model_version,
            'rmse': run.rmse,
            'mae': run.mae,
            'artifact_exists': candidate_artifact.exists(),
        })
    last_training = retraining_history[0] if retraining_history else None
    api_status = _get_api_status()

    if last_training:
        production_model_version = last_training.model_version
        dataset_version = last_training.dataset_version
        last_training_date = last_training.training_date.strftime('%Y-%m-%d %H:%M:%S')
        production_model_name = last_training.model_name
    else:
        production_model_version = 'N/A'
        dataset_version = 'N/A'
        last_training_date = 'N/A'
        production_model_name = report.get('best_model', 'N/A') if report else 'N/A'

    if not production_model_exists:
        production_model_name = f"{production_model_name} (missing artifact)"

    if avg_prediction_error is None:
        model_health = 'No data'
    elif avg_prediction_error <= 5:
        model_health = 'Excellent'
    elif avg_prediction_error <= 10:
        model_health = 'Good'
    elif avg_prediction_error <= 20:
        model_health = 'Moderate'
    else:
        model_health = 'Needs review'

    context = {
        'username': username,
        'artifact_files': artifact_files,
        'model_dir': str(models_dir),
        'artifact_count': len(artifact_files),
        'report_available': report_present,
        'report_path': str(report_path) if report_present else 'Not available',
        'report_modified_at': report_modified_at,
        'report_excerpt': report_excerpt,
        'top_models': top_models,
        'total_predictions': total_predictions,
        'avg_prediction_error': round(avg_prediction_error, 2) if avg_prediction_error is not None else None,
        'status_breakdown': status_breakdown,
        'last_prediction': last_prediction,
        'retraining_history': retraining_history_items,
        'production_model_version': production_model_version,
        'dataset_version': dataset_version,
        'last_training_date': last_training_date,
        'production_model_name': production_model_name,
        'production_model_exists': production_model_exists,
        'model_health': model_health,
        'api_status': api_status,
        'row_count': report.get('rows', 0) if report else 0,
    }
    return render(request, 'ModelMonitoring.html', context)


def _parse_duration_to_minutes(duration):
    if pd.isna(duration):
        return 0
    if isinstance(duration, str):
        parts = re.findall(r'\d+', duration)
        if not parts:
            return 0
        if len(parts) >= 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(parts[0]) * 60
    return int(duration)


def _parse_time_component(value):
    if pd.isna(value):
        return 0

    text = str(value).strip()
    if not text:
        return 0

    if ':' in text:
        parts = text.split(':', 1)
        try:
            return int(parts[0])
        except ValueError:
            digits = re.findall(r'\d+', text)
            return int(digits[0]) if digits else 0

    digits = re.findall(r'\d+', text)
    return int(digits[0]) if digits else 0


def _parse_time_minutes(value):
    if pd.isna(value):
        return 0

    text = str(value).strip()
    if not text:
        return 0

    if ':' in text:
        parts = text.split(':', 1)
        try:
            hour = int(parts[0])
            minute = int(parts[1].split()[0])
            return hour * 60 + minute
        except (ValueError, IndexError):
            digits = re.findall(r'\d+', text)
            return int(digits[0]) if digits else 0

    digits = re.findall(r'\d+', text)
    return int(digits[0]) if digits else 0


def _prepare_feature_frame(dataframe):
    data = dataframe.copy()
    data['Date_of_Journey'] = pd.to_datetime(data['Date_of_Journey'], errors='coerce')
    data['day'] = data['Date_of_Journey'].dt.day
    data['month'] = data['Date_of_Journey'].dt.month
    data['year'] = data['Date_of_Journey'].dt.year
    data['day_of_week'] = data['Date_of_Journey'].dt.dayofweek

    dep_time = data['Dep_Time'].astype(str).str.split(':', n=1, expand=True)
    arrival_time = data['Arrival_Time'].astype(str).str.split(':', n=1, expand=True)
    data['dep_hour'] = dep_time[0].apply(_parse_time_component)
    data['dep_minute'] = dep_time[1].apply(_parse_time_component)
    data['arrival_hour'] = arrival_time[0].apply(_parse_time_component)
    data['arrival_minute'] = arrival_time[1].apply(_parse_time_component)
    data['duration_minutes'] = data['Duration'].apply(_parse_duration_to_minutes)

    data['Airline'] = data['Airline'].astype(str).str.strip()
    data['Source'] = data['Source'].astype(str).str.strip()
    data['Destination'] = data['Destination'].astype(str).str.strip()

    return data.drop(columns=['Date_of_Journey', 'Dep_Time', 'Arrival_Time', 'Duration'], errors='ignore')


def _make_prediction_row(airline, source, dest, dd, mm, yy):
    global dataset
    if dataset is None:
        dataset = load_dataset()

    dep_time_values = dataset['Dep_Time'].astype(str).str.split(':', n=1, expand=True)
    arrival_time_values = dataset['Arrival_Time'].astype(str).str.split(':', n=1, expand=True)
    duration_values = dataset['Duration'].apply(_parse_duration_to_minutes)

    dep_hour = int(dep_time_values[0].apply(_parse_time_component).mean())
    dep_minute = int(dep_time_values[1].apply(_parse_time_component).mean()) if len(dep_time_values.columns) > 1 else 0
    arrival_hour = int(arrival_time_values[0].apply(_parse_time_component).mean())
    arrival_minute = int(arrival_time_values[1].apply(_parse_time_component).mean()) if len(arrival_time_values.columns) > 1 else 0

    row = {
        'Airline': str(airline or '').strip(),
        'Source': str(source or '').strip(),
        'Destination': str(dest or '').strip(),
        'day': int(dd),
        'month': int(mm),
        'year': int(yy),
        'day_of_week': pd.Timestamp(f'{yy}-{mm}-{dd}').dayofweek,
        'dep_hour': dep_hour,
        'dep_minute': dep_minute,
        'arrival_hour': arrival_hour,
        'arrival_minute': arrival_minute,
        'duration_minutes': int(duration_values.mean()),
    }
    return pd.DataFrame([row])


def _initialize_prediction_pipeline():
    global dataset, le1, le2, le3, scaler, X, Y, rf, feature_columns

    if dataset is None:
        dataset = load_dataset()

    if le1 is None or le2 is None or le3 is None or scaler is None or X is None or Y is None or rf is None:
        training_frame = _prepare_feature_frame(dataset.copy())
        training_frame['Price'] = dataset['Price'].astype(float)
        Y = np.asarray(training_frame['Price']).ravel()
        model_frame = training_frame.drop(columns=['Price'])

        le1 = LabelEncoder()
        le2 = LabelEncoder()
        le3 = LabelEncoder()
        model_frame['Airline'] = pd.Series(le1.fit_transform(model_frame['Airline'].astype(str)))
        model_frame['Source'] = pd.Series(le2.fit_transform(model_frame['Source'].astype(str)))
        model_frame['Destination'] = pd.Series(le3.fit_transform(model_frame['Destination'].astype(str)))

        feature_columns = list(model_frame.columns)
        scaler = MinMaxScaler()
        X = scaler.fit_transform(model_frame)

        X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.2, random_state=42)
        rf = RandomForestRegressor(n_estimators=300, max_depth=20, min_samples_leaf=2, max_features='sqrt', random_state=42, n_jobs=-1)
        rf.fit(X_train, y_train)

    return le1, le2, le3, scaler, rf


def _get_model_metrics():
    global X, Y, rf
    if X is None or Y is None or rf is None:
        _initialize_prediction_pipeline()

    X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.2, random_state=42)
    predictions = rf.predict(X_test)
    mse = np.mean((y_test - predictions) ** 2)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(y_test - predictions))
    return rmse, mae


def _evaluate_models():
    global X, Y
    if X is None or Y is None:
        _initialize_prediction_pipeline()

    X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.2, random_state=42)
    models = {
        'Linear Regression': LinearRegression(),
        'Decision Tree': DecisionTreeRegressor(random_state=42),
        'Random Forest': RandomForestRegressor(n_estimators=300, max_depth=20, min_samples_leaf=2, max_features='sqrt', random_state=42, n_jobs=-1),
        'Gradient Boosting': GradientBoostingRegressor(random_state=42),
    }

    results = []
    for name, model in models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
        mae = float(mean_absolute_error(y_test, preds))
        r2 = float(r2_score(y_test, preds))
        results.append((name, rmse, mae, r2))

    results.sort(key=lambda item: item[1])
    best_name, best_rmse, best_mae, best_r2 = results[0]
    return results, best_name, best_rmse, best_mae, best_r2


def _get_feature_importance():
    global rf, feature_columns
    if rf is None or feature_columns is None:
        _initialize_prediction_pipeline()

    importances = rf.feature_importances_
    ranked = sorted(zip(feature_columns, importances), key=lambda item: item[1], reverse=True)
    return ranked[:8]


def _get_airport_code(city_name):
    mapping = {
        'bangalore': 'BLR',
        'bengaluru': 'BLR',
        'delhi': 'DEL',
        'new delhi': 'DEL',
        'mumbai': 'BOM',
        'kolkata': 'CCU',
        'chennai': 'MAA',
        'hyderabad': 'HYD',
        'pune': 'PNQ',
        'cochin': 'COK',
        'kochi': 'COK',
        'ahmedabad': 'AMD',
        'jaipur': 'JAI',
        'goa': 'GOI',
    }
    if not city_name:
        return None
    normalized = str(city_name).strip().lower()
    return mapping.get(normalized)


def _find_price_value(payload):
    price_keys = {'price', 'amount', 'value', 'fare', 'total'}
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() in price_keys:
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str):
                    try:
                        return float(value.replace(',', '').strip())
                    except ValueError:
                        pass
            found = _find_price_value(value)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_price_value(item)
            if found is not None:
                return found
    return None


def _get_live_price_signal(airline, source, dest, dd, mm, yy):
    general_price = _get_general_price_estimate(airline, source, dest)
    return {
        'price': round(float(general_price) * 1.04, 2),
        'source': 'fallback',
        'note': 'Live fare signal is unavailable. Showing the fallback benchmark based on the general price estimate.'
    }


def _get_general_price_estimate(airline, source, dest):
    global dataset

    if dataset is None:
        dataset = load_dataset()

    filtered = dataset.copy()
    filtered['Airline'] = filtered['Airline'].astype(str).str.lower()
    filtered['Source'] = filtered['Source'].astype(str).str.lower()
    filtered['Destination'] = filtered['Destination'].astype(str).str.lower()

    if airline:
        filtered = filtered[filtered['Airline'] == str(airline).lower()]
    if source:
        filtered = filtered[filtered['Source'] == str(source).lower()]
    if dest:
        filtered = filtered[filtered['Destination'] == str(dest).lower()]

    if filtered.empty:
        filtered = dataset.copy()

    if filtered.empty:
        return round(float(dataset['Price'].mean()), 2)

    return round(float(filtered['Price'].mean()), 2)


@require_login
@require_login
def PredictPrices(request):
    if request.method == 'GET':
        # Provide dynamic day/month/year ranges to template
        start_year = datetime.now().year
        years = [str(y) for y in range(start_year, start_year + 28)]
        months = [f"{i:02d}" for i in range(1, 13)]
        days = [f"{i:02d}" for i in range(1, 32)]

        try:
            dataset_ref = load_dataset()
            airline_options = dataset_ref['Airline'].astype(str).str.strip().dropna().unique().tolist()
            city_options = list(dict.fromkeys(
                dataset_ref['Source'].astype(str).str.strip().dropna().tolist() +
                dataset_ref['Destination'].astype(str).str.strip().dropna().tolist() +
                ['Delhi', 'Mumbai', 'Banglore', 'Chennai', 'Kolkata', 'Hyderabad', 'Pune', 'Cochin', 'New Delhi']
            ))

            stop_labels = []
            for value in dataset_ref['Total_Stops'].astype(str).str.strip().dropna().tolist():
                lowered = value.lower()
                if 'non-stop' in lowered or 'non stop' in lowered:
                    label = 'Non-stop'
                elif '1' in lowered:
                    label = '1 stop'
                elif '2' in lowered:
                    label = '2 stops'
                else:
                    label = '3+ stops'
                if label not in stop_labels:
                    stop_labels.append(label)
            stops_options = stop_labels or ['Non-stop', '1 stop', '2 stops', '3+ stops']

            info_values = dataset_ref['Additional_Info'].astype(str).str.strip().dropna().tolist()
            travel_class_options = ['Normal class']
            if any('business class' in str(value).lower() for value in info_values):
                travel_class_options = ['Business class', 'Normal class']
        except Exception:
            airline_options = [
                'IndiGo', 'Air India', 'SpiceJet', 'Vistara', 'GoAir', 'Air Asia', 'Jet Airways',
                'Jet Airways Business', 'Multiple carriers', 'Premium', 'Trujet', 'Vistara Premium'
            ]
            city_options = ['Delhi', 'Mumbai', 'Banglore', 'Chennai', 'Kolkata', 'Hyderabad', 'Pune', 'Cochin', 'New Delhi']
            stops_options = ['Non-stop', '1 stop', '2 stops', '3+ stops']
            travel_class_options = ['Business class', 'Normal class']

        context = {
            'day_range': days,
            'month_range': months,
            'year_range': years,
            'selected_day': None,
            'selected_month': None,
            'selected_year': None,
            'selected_airline': '',
            'selected_source': '',
            'selected_dest': '',
            'selected_stops': '',
            'selected_travel_class': '',
            'airline_options': airline_options,
            'city_options': city_options,
            'stops_options': stops_options,
            'travel_class_options': travel_class_options,
        }
        return render(request, 'PredictPrices.html', context)

@require_login
def PredictPricesAction(request):
    if request.method == 'POST':
        username = request.session.get('username', '')
        global dataset, le1, le2, le3, scaler, X, Y, rf, feature_columns
        dd = request.POST.get('t1', False)
        mm = request.POST.get('t2', False)
        yy = request.POST.get('t3', False)
        airline = request.POST.get('t4', False)
        source = request.POST.get('t5', False)
        dest = request.POST.get('t6', False)
        stops = request.POST.get('stops', False)
        travel_class = request.POST.get('travel_class', False)

        # Validate that source and destination are not the same
        if source and dest and str(source).strip().lower() == str(dest).strip().lower():
            _safe_messages_error(request, 'Source and destination cannot be the same. Please choose different cities.')
            # Re-render the form with previous inputs and ranges
            start_year = datetime.now().year
            years = [str(y) for y in range(start_year, start_year + 28)]
            months = [f"{i:02d}" for i in range(1, 13)]
            days = [f"{i:02d}" for i in range(1, 32)]
            airline_options = [
                'IndiGo', 'Air India', 'SpiceJet', 'Vistara', 'GoAir', 'Air Asia', 'Jet Airways',
                'Jet Airways Business', 'Multiple carriers', 'Premium', 'Trujet', 'Vistara Premium'
            ]
            city_options = ['Delhi', 'Mumbai', 'Banglore', 'Chennai', 'Kolkata', 'Hyderabad', 'Pune', 'Cochin', 'New Delhi']

            context = {
                'day_range': days,
                'month_range': months,
                'year_range': years,
                'selected_day': dd or None,
                'selected_month': mm or None,
                'selected_year': yy or None,
                'selected_airline': airline or '',
                'selected_source': source or '',
                'selected_dest': dest or '',
                'selected_stops': stops or '',
                'selected_travel_class': travel_class or '',
                'airline_options': airline_options,
                'city_options': city_options,
                'stops_options': ['Non-stop', '1 stop', '2 stops', '3+ stops'],
                'travel_class_options': ['Business class', 'Normal class'],
            }
            return render(request, 'PredictPrices.html', context)

        # Ensure dataset is loaded so we can validate inputs against known values
        try:
            if dataset is None:
                dataset = load_dataset()
        except Exception as e:
            _safe_messages_error(request, f'Could not load dataset for validation: {e}')
            return redirect('/PredictPrices')

        # Build sets of valid, lowercased values and normalize common user aliases
        valid_airlines = set(dataset['Airline'].astype(str).str.strip().str.lower())
        valid_sources = set(dataset['Source'].astype(str).str.strip().str.lower())
        valid_dests = set(dataset['Destination'].astype(str).str.strip().str.lower())

        city_aliases = {
            'bangalore': 'Banglore',
            'bengaluru': 'Banglore',
            'new delhi': 'New Delhi',
            'newdelhi': 'New Delhi',
            'cochin': 'Cochin',
            'kochi': 'Cochin',
        }
        airline_aliases = {
            'airindia': 'Air India',
            'air india': 'Air India',
            'airasia': 'Air Asia',
            'goair': 'GoAir',
            'go air': 'GoAir',
            'jet airways': 'Jet Airways',
            'jetairways': 'Jet Airways',
            'jet airways business': 'Jet Airways Business',
            'jetairwaysbusiness': 'Jet Airways Business',
            'vistara premium': 'Vistara Premium',
            'vistarapremium': 'Vistara Premium',
            'multiple carriers': 'Multiple carriers',
            'multiplecarriers': 'Multiple carriers',
            'spicejet': 'SpiceJet',
            'indigo': 'IndiGo',
        }

        def _resolve_canonical(value, source_series, aliases=None, error_label='value'):
            if value is None:
                return None, False
            text = str(value).strip()
            if not text:
                return '', False
            lowered = text.lower()
            if aliases and lowered in aliases:
                return aliases[lowered], True
            lookup = {
                str(item).strip().lower(): str(item).strip()
                for item in source_series.astype(str).tolist()
            }
            if lowered in lookup:
                return lookup[lowered], False
            matches = difflib.get_close_matches(lowered, list(lookup.keys()), n=1, cutoff=0.6)
            if matches:
                return lookup[matches[0]], True
            return text, False

        # Helper to suggest close matches
        def _suggest(value, candidates):
            if not value:
                return None
            value_l = str(value).strip().lower()
            matches = difflib.get_close_matches(value_l, list(candidates), n=1, cutoff=0.6)
            return matches[0] if matches else None

        airline, airline_changed = _resolve_canonical(airline, dataset['Airline'], aliases=airline_aliases)
        if airline_changed and airline:
            _safe_messages_info(request, f"Interpreting airline '{request.POST.get('t4')}' as '{airline}'.")

        source, source_changed = _resolve_canonical(source, dataset['Source'], aliases=city_aliases)
        if source_changed and source:
            _safe_messages_info(request, f"Interpreting source '{request.POST.get('t5')}' as '{source}'.")

        dest, dest_changed = _resolve_canonical(dest, dataset['Destination'], aliases=city_aliases)
        if dest_changed and dest:
            _safe_messages_info(request, f"Interpreting destination '{request.POST.get('t6')}' as '{dest}'.")

        # Validate airline with graceful fallback so the form will still estimate a fare
        if airline and str(airline).strip().lower() not in valid_airlines:
            suggestion = _suggest(airline, valid_airlines)
            if suggestion:
                canonical_airline = next(s for s in dataset['Airline'].astype(str).tolist() if s.strip().lower() == suggestion)
                airline = canonical_airline
                _safe_messages_info(request, f"Interpreting airline '{request.POST.get('t4')}' as '{canonical_airline}'.")
                valid_airlines = set(dataset['Airline'].astype(str).str.strip().str.lower())
            else:
                _safe_messages_info(request, f"Airline '{airline}' is not present in the current training sample. The application will continue using the closest market benchmark.")

        # Validate source with a graceful fallback for cities not present in the sampled training data
        if source and str(source).strip().lower() not in valid_sources:
            suggestion = _suggest(source, valid_sources)
            if suggestion:
                canonical = next(s for s in dataset['Source'].astype(str).tolist() if s.strip().lower() == suggestion)
                source = canonical
                _safe_messages_info(request, f"Interpreting source '{request.POST.get('t5')}' as '{canonical}'.")
                valid_sources = set(dataset['Source'].astype(str).str.strip().str.lower())
            else:
                _safe_messages_info(request, f"Source '{source}' is not present in the current training sample. The application will continue using the closest market benchmark.")

        # Validate destination with a graceful fallback for cities not present in the sampled training data
        if dest and str(dest).strip().lower() not in valid_dests:
            suggestion = _suggest(dest, valid_dests)
            if suggestion:
                canonical_dest = next(s for s in dataset['Destination'].astype(str).tolist() if s.strip().lower() == suggestion)
                dest = canonical_dest
                _safe_messages_info(request, f"Interpreting destination '{request.POST.get('t6')}' as '{canonical_dest}'.")
                valid_dests = set(dataset['Destination'].astype(str).str.strip().str.lower())
            else:
                _safe_messages_info(request, f"Destination '{dest}' is not present in the current training sample. The application will continue using the closest market benchmark.")

        # Use ML wrapper for prediction (will train on-demand if necessary)
        try:
            ml_res = predict_price(airline, source, dest, dd, mm, yy, stops=stops, travel_class=travel_class)
            predict = ml_res.get('prediction')
            general_price = ml_res.get('general_price')
        except Exception as e:
            messages.error(request, f'Prediction failed: {e}')
            return redirect('/PredictPrices')

        live_signal = _get_live_price_signal(airline, source, dest, dd, mm, yy)
        live_price = float(live_signal.get('price', 0.0) or 0.0)
        difference = round(predict - live_price, 2)
        percentage_error = round(abs(difference / live_price) * 100, 2) if live_price != 0 else None
        if percentage_error is not None:
            if percentage_error < 5:
                prediction_status = 'Excellent'
            elif percentage_error < 10:
                prediction_status = 'Good'
            elif percentage_error < 15:
                prediction_status = 'Moderate'
            else:
                prediction_status = 'Poor'
        else:
            prediction_status = 'Unknown'

        PredictionHistory.objects.create(
            username=username,
            airline=airline or '',
            source=source or '',
            destination=dest or '',
            travel_date=datetime.strptime(f"{yy}-{mm}-{dd}", '%Y-%m-%d').date(),
            predicted_price=predict,
            historical_average=general_price,
            live_price=live_price,
            selected_model=ml_res.get('selected_model', 'production_model'),
            difference=difference,
            percentage_error=percentage_error or 0.0,
            status=prediction_status,
            currency=live_signal.get('currency', 'INR') or 'INR',
            booking_link=live_signal.get('booking_link', ''),
            flight_number=live_signal.get('flight_number', ''),
        )

        try:
            _save_prediction_history_report()
        except Exception:
            pass

        output = (
            f"<div class='hero'>"
            f"<div class='pill'>Forecast Summary</div>"
            f"<div class='price'>₹{predict}</div>"
            f"<div><strong>Estimated flight fare</strong> for your selected route and travel date.</div>"
            f"</div>"
            f"<div class='metrics'>"
            f"<div class='metric'><div class='label'>General Price</div><div class='value'>₹{general_price:.2f}</div></div>"
            f"<div class='metric'><div class='label'>Live Market Signal</div><div class='value'>₹{live_signal['price']:.2f}</div></div>"
            f"</div>"
            f"<div class='info-note'>"
            f"<p><strong>Note:</strong> General Price is the historical average route fare. Forecasted fare is model-based and route/date-specific, so it may differ.</p>"
            f"<p><strong>Live Market Signal:</strong> Live fare signal fetched from the configured API.</p>"
            f"</div>"
        )
        context= {'data': output}
        return render(request, 'UserScreen.html', context)
        







        
