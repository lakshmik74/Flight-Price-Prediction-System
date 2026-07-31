from django.test import Client, RequestFactory, TestCase, TransactionTestCase
from rest_framework.test import APIClient
from unittest.mock import patch
from pathlib import Path
from . import views
import joblib
import shutil


class PredictPricesActionTests(TestCase):
    def test_predict_prices_initializes_training_artifacts(self):
        views.le1 = None
        views.le2 = None
        views.le3 = None
        views.scaler = None
        views.rf = None
        views.dataset = None
        views.X = None
        views.Y = None

        request = RequestFactory().post(
            '/PredictPricesAction',
            {
                't1': '02',
                't2': '03',
                't3': '2023',
                't4': 'airindia',
                't5': 'chennai',
                't6': 'banglore',
            },
        )

        response = views.PredictPricesAction(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Estimated fare')
        self.assertContains(response, 'General Price')
        self.assertContains(response, 'Live Market Signal')

    def test_predict_prices_handles_arrival_times_with_date_suffix(self):
        views.le1 = None
        views.le2 = None
        views.le3 = None
        views.scaler = None
        views.rf = None
        views.dataset = None
        views.X = None
        views.Y = None

        request = RequestFactory().post(
            '/PredictPricesAction',
            {
                't1': '10',
                't2': '06',
                't3': '2024',
                't4': 'Jet Airways',
                't5': 'Delhi',
                't6': 'Cochin',
            },
        )

        response = views.PredictPricesAction(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Estimated fare')


class AdminPanelTests(TransactionTestCase):
    def setUp(self):
        self.client = Client()
        session = self.client.session
        session['username'] = 'testuser'
        session.save()

    def test_admin_panel_requires_login(self):
        anon = Client()
        response = anon.get('/AdminPanel')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/UserLogin', response.url)

    def test_admin_download_requires_login(self):
        anon = Client()
        response = anon.get('/AdminDownload/test_artifact.joblib')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/UserLogin', response.url)

    def test_admin_retrain_requires_login(self):
        anon = Client()
        response = anon.post('/AdminRetrain')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/UserLogin', response.url)

    def test_admin_clear_artifacts_requires_login(self):
        anon = Client()
        response = anon.post('/AdminClearArtifacts')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/UserLogin', response.url)

    def test_dashboard_requires_login(self):
        anon = Client()
        response = anon.get('/Dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/UserLogin', response.url)

    def test_trainml_requires_login(self):
        anon = Client()
        response = anon.get('/TrainML')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/UserLogin', response.url)

    def test_modelreport_requires_login(self):
        anon = Client()
        response = anon.get('/ModelReport')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/UserLogin', response.url)

    def test_modelmonitoring_requires_login(self):
        anon = Client()
        response = anon.get('/ModelMonitoring')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/UserLogin', response.url)

    def test_api_predict_returns_success(self):
        response = self.client.post('/api/predict/', {
            'airline': 'Air India',
            'source': 'Delhi',
            'destination': 'Mumbai',
            'day': 10,
            'month': 10,
            'year': 2025,
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('success'))
        self.assertIn('prediction', response.json().get('data', {}))

    def test_api_models_list_returns_json(self):
        response = self.client.get('/api/models/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('success'))
        self.assertIsInstance(response.json().get('models'), list)

    def test_api_history_returns_retraining_records(self):
        from .models import RetrainingHistory
        RetrainingHistory.objects.create(
            model_name='test-model',
            model_version='v1',
            dataset_version='testdata',
            rmse=100.0,
            mae=50.0,
            training_time_seconds=10.0,
            model_path='models/v1_test-model.joblib',
            is_production=True,
        )
        response = self.client.get('/api/history/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.json())

    def test_api_retrain_requires_login(self):
        anon = Client()
        response = anon.post('/api/retrain/')
        self.assertEqual(response.status_code, 403)

    def test_api_health_returns_status(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('status'), 'healthy')

    def test_predictprices_requires_login(self):
        anon = Client()
        response = anon.get('/PredictPrices')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/UserLogin', response.url)

    def test_admin_panel_renders_for_authenticated_user(self):
        response = self.client.get('/AdminPanel')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Panel')
        self.assertContains(response, 'Retrain production model')

    def test_admin_panel_renders_with_report_file(self):
        reports_dir = Path(__file__).resolve().parents[2] / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / 'model_comparison.json'
        report_path.write_text('{"best_model":"random_forest","rows":10}')

        response = self.client.get('/AdminPanel')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Panel')
        self.assertContains(response, 'Retrain production model')
        self.assertContains(response, 'random_forest')

        report_path.unlink()

    def test_modelmonitoring_renders_for_authenticated_user(self):
        response = self.client.get('/ModelMonitoring')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Model Monitoring')
        self.assertContains(response, 'Production model version')

    @patch('FlightPrice.views.train_pipeline')
    def test_admin_retrain_posts_and_redirects(self, mock_train_pipeline):
        mock_train_pipeline.return_value = {
            'best_model': 'random_forest',
            'rmse': 210.0,
            'mae': 150.0,
            'candidate_models': []
        }
        response = self.client.post('/AdminRetrain')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/AdminPanel')

    def test_admin_clear_artifacts_posts_and_redirects(self):
        response = self.client.post('/AdminClearArtifacts')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/AdminPanel')

    def test_admin_download_artifact_returns_file(self):
        # Ensure a file exists in the models directory for the download test
        models_dir = Path(__file__).resolve().parents[2] / 'models'
        models_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = models_dir / 'test_artifact.joblib'
        artifact_path.write_text('dummy')

        response = self.client.get('/AdminDownload/test_artifact.joblib')
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment; filename="test_artifact.joblib"', response.get('Content-Disposition'))
        response.close()

        artifact_path.unlink()

    def test_admin_promote_artifact_posts_and_redirects(self):
        models_dir = Path(__file__).resolve().parents[2] / 'models'
        models_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = models_dir / 'v1_testmodel.joblib'
        artifact_path.write_bytes(b'dummy-model-bytes')

        response = self.client.post(f'/AdminPromote/{artifact_path.name}')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/ModelMonitoring')

        prod = models_dir / 'production_model.joblib'
        self.assertTrue(prod.exists())
        self.assertEqual(prod.read_bytes(), b'dummy-model-bytes')

        meta_path = models_dir / 'model_metadata.joblib'
        self.assertTrue(meta_path.exists())
        meta = joblib.load(str(meta_path))
        self.assertEqual(meta.get('model_version'), artifact_path.name.replace('.joblib', ''))

        artifact_path.unlink()
        prod.unlink()
        meta_path.unlink()

    def test_admin_promote_nonexistent_artifact_redirects_without_creating_files(self):
        models_dir = Path(__file__).resolve().parents[2] / 'models'
        models_dir.mkdir(parents=True, exist_ok=True)
        # Ensure no production or metadata exist before
        prod = models_dir / 'production_model.joblib'
        meta_path = models_dir / 'model_metadata.joblib'
        if prod.exists():
            prod.unlink()
        if meta_path.exists():
            meta_path.unlink()

        response = self.client.post('/AdminPromote/nonexistent_model.joblib')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/ModelMonitoring')

        self.assertFalse(prod.exists())
        self.assertFalse(meta_path.exists())

    def test_admin_rollback_artifact_posts_and_restores_previous(self):
        models_dir = Path(__file__).resolve().parents[2] / 'models'
        models_dir.mkdir(parents=True, exist_ok=True)
        a = models_dir / 'v1_a.joblib'
        b = models_dir / 'v2_b.joblib'
        a.write_bytes(b'first')
        b.write_bytes(b'second')

        # Promote 'a' then promote 'b'
        self.client.post(f'/AdminPromote/{a.name}')
        self.client.post(f'/AdminPromote/{b.name}')

        prod = models_dir / 'production_model.joblib'
        self.assertTrue(prod.exists())
        self.assertEqual(prod.read_bytes(), b'second')

        # Rollback to 'a'
        response = self.client.post(f'/AdminRollback/{a.name}')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/ModelMonitoring')

        self.assertTrue(prod.exists())
        self.assertEqual(prod.read_bytes(), b'first')

        # cleanup
        a.unlink()
        b.unlink()
        if prod.exists():
            prod.unlink()
        meta = models_dir / 'model_metadata.joblib'
        if meta.exists():
            meta.unlink()

    def test_admin_retrain_archives_previous_production(self):
        models_dir = Path(__file__).resolve().parents[2] / 'models'
        models_dir.mkdir(parents=True, exist_ok=True)
        prod = models_dir / 'production_model.joblib'
        meta = models_dir / 'model_metadata.joblib'
        prod.write_bytes(b'old')
        import joblib
        joblib.dump({'best_model_metrics': {'rmse': 9999}}, str(meta))

        response = self.client.post('/AdminRetrain')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/AdminPanel')

        archive_dir = models_dir / 'archive'
        self.assertTrue(archive_dir.exists())
        archived = list(archive_dir.glob('production_*.joblib'))
        self.assertTrue(len(archived) >= 1)

        # cleanup artifacts generated by training
        prod.unlink(missing_ok=True)
        meta.unlink(missing_ok=True)
        if archive_dir.exists():
            shutil.rmtree(archive_dir, ignore_errors=True)

    def test_admin_download_report_file_returns_file(self):
        reports_dir = Path(__file__).resolve().parents[2] / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / 'model_comparison.json'
        report_path.write_text('{"best_model":"random_forest","rows":10}')

        response = self.client.get('/AdminDownload/model_comparison.json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment; filename="model_comparison.json"', response.get('Content-Disposition'))
        response.close()

        report_path.unlink()

    def test_admin_download_artifact_not_found(self):
        response = self.client.get('/AdminDownload/does_not_exist.joblib')
        self.assertEqual(response.status_code, 404)

    def test_admin_clean_retraining_removes_missing_artifacts(self):
        models_dir = Path(__file__).resolve().parents[2] / 'models'
        models_dir.mkdir(parents=True, exist_ok=True)
        # existing artifact
        existing = models_dir / 'v_exists.joblib'
        existing.write_bytes(b'data')

        from .models import RetrainingHistory
        RetrainingHistory.objects.create(
            model_name='exists',
            model_version='v_exists',
            dataset_version='test',
            rmse=0.0,
            mae=0.0,
            training_time_seconds=0.0,
            model_path=str(existing),
            is_production=False,
        )
        RetrainingHistory.objects.create(
            model_name='missing',
            model_version='v_missing',
            dataset_version='test',
            rmse=0.0,
            mae=0.0,
            training_time_seconds=0.0,
            model_path='models/v_missing.joblib',
            is_production=False,
        )

        response = self.client.post('/AdminCleanRetraining')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/AdminPanel')

        remaining = list(RetrainingHistory.objects.values_list('model_version', flat=True))
        self.assertIn('v_exists', remaining)
        self.assertNotIn('v_missing', remaining)

        existing.unlink()

    def test_report_notification_sends_email(self):
        from django.test import override_settings
        from django.core import mail
        from FlightPrice.ml import model as ml_model

        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', REPORT_NOTIFY_TO=['notify@example.com'], DEFAULT_FROM_EMAIL='noreply@example.com'):
            best = {'name': 'unittest_model', 'model_version': 'v1', 'rmse': 1.23, 'mae': 0.5, 'r2': 0.99}
            reports_dir = Path(__file__).resolve().parents[2] / 'reports'
            reports_dir.mkdir(parents=True, exist_ok=True)
            report_path = ml_model._save_report(best, [], ['f1', 'f2'], 10, training_time_seconds=0.5)

            # Report file should be created and an email should have been sent
            self.assertTrue(Path(report_path).exists())
            self.assertEqual(len(mail.outbox), 1)
            self.assertIn('Model report updated', mail.outbox[0].subject)

            # cleanup generated report artifacts
            try:
                for p in reports_dir.glob('model_comparison*'):
                    p.unlink()
            except Exception:
                pass
            log = reports_dir / 'report_changes.log'
            if log.exists():
                log.unlink()
