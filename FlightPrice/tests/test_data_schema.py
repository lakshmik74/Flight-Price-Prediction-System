import os
import pandas as pd
import unittest
from FlightPrice.ml.data import load_dataset, validate_dataset_schema

class TestDatasetSchemaValidation(unittest.TestCase):
    def test_validate_dataset_success(self):
        df = pd.DataFrame({
            'Date_of_Journey': ['01/01/2023'],
            'Dep_Time': ['10:00'],
            'Arrival_Time': ['12:00'],
            'Duration': ['2h 0m'],
            'Total_Stops': ['non-stop'],
            'Airline': ['Air India'],
            'Source': ['Delhi'],
            'Destination': ['Mumbai'],
            'Additional_Info': ['No info'],
            'Price': [5000],
        })
        self.assertTrue(validate_dataset_schema(df))

    def test_validate_dataset_missing_columns(self):
        df = pd.DataFrame({
            'Date_of_Journey': ['01/01/2023'],
            'Dep_Time': ['10:00'],
            'Price': [5000],
        })
        with self.assertRaises(ValueError) as cm:
            validate_dataset_schema(df)
        self.assertIn('Missing required columns', str(cm.exception))

    def test_load_dataset_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_dataset(path='nonexistent_dataset.csv')

if __name__ == '__main__':
    unittest.main()
