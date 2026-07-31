import os
import unittest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Flight.settings')
import django
django.setup()

from FlightPrice.ml.data import load_dataset
from FlightPrice.ml.features import prepare_feature_frame

class TestMLModule(unittest.TestCase):
    def test_load_dataset(self):
        df = load_dataset()
        self.assertIsNotNone(df)
        self.assertIn('Price', df.columns)

    def test_prepare_features(self):
        df = load_dataset().head(5)
        f = prepare_feature_frame(df)
        self.assertIn('day', f.columns)
        self.assertIn('duration_minutes', f.columns)


class PredictPricesActionAliasTests(unittest.TestCase):
    def test_predict_prices_normalizes_airline_and_city_aliases(self):
        from django.test import RequestFactory
        from FlightPrice import views
        from FlightPrice.models import PredictionHistory

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
                't3': '2025',
                't4': 'airindia',
                't5': 'Bangalore',
                't6': 'Cochin',
            },
        )
        request.session = {'username': 'alias-test'}

        response = views.PredictPricesAction(request)
        response_html = response.content.decode('utf-8', errors='ignore')

        self.assertEqual(response.status_code, 200)
        self.assertIn('Estimated fare', response_html)

        latest = PredictionHistory.objects.order_by('-id').first()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.airline, 'Air India')
        self.assertEqual(latest.source, 'Banglore')
        self.assertEqual(latest.destination, 'Cochin')

if __name__ == '__main__':
    unittest.main()
