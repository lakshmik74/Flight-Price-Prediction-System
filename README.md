# FlightPrice Prediction Project

A Django-based flight price prediction application that combines historical fare data, model-based forecasted prices, and route-level live market signal summaries.

## What this project does

- Supports user registration and login
- Uses historical route data for a baseline average fare
- Predicts route/date-specific fares with a trained machine learning model
- Displays the prediction alongside a live-market signal note
- Provides dataset views, admin reporting, and model training utilities

## Key behavior

- **General Price** is the historical average fare for a selected route.
- **Forecasted fare** is a route/date-specific machine learning estimate and may differ from the average price.
- **Live Market Signal** is currently shown as a fallback summary note and does not rely on a live API fetch in the current implementation.

## Requirements

- Python 3.11+ (recommended)
- MySQL server (optional if you want the configured MySQL backend)
- `pip` for installing Python dependencies

## Install

From the project root (`FlightPrice`):

```bash
pip install -r requirements.txt
```

## Setup

1. Create the MySQL database and user as needed.
2. Update the MySQL settings in `Flight/settings.py` if required.
3. Run Django migrations:

```bash
python manage.py migrate
```

## Run the app

From the project root:

```bash
python manage.py runserver 8000
```

Or use the included launcher script from the same root:

```bash
python run_mysql.py
```

Then open:

```
http://127.0.0.1:8000/
```

## Project layout

This repository has three nested levels:
- outer `FlightPrice/` is the repository root
- inner `FlightPrice/` is the Django project root containing `manage.py`
- inner `FlightPrice/FlightPrice/` is the main Django app package

```
FlightPrice/              (repo root)
├── .env
├── .gitignore
├── .idea/
├── .venv/
├── catboost_info/
├── data/
│   └── raw/
│       └── FlightPrice.csv
├── FlightPrice/          (Django project root)
│   ├── .env
│   ├── DB.txt
│   ├── docs/
│   ├── Flight/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── FlightPrice/      (main Django app package)
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── api_urls.py
│   │   ├── api_views.py
│   │   ├── Github FlightPrice Prediction.ipynb
│   │   ├── management/
│   │   ├── migrations/
│   │   ├── ml/
│   │   ├── models/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── static/
│   │   ├── templates/
│   │   ├── tests/
│   │   ├── tests.py
│   │   ├── urls.py
│   │   ├── utils.py
│   │   └── views.py
│   ├── manage.py
│   ├── README.md
│   ├── requirements.txt
│   ├── run.bat
│   ├── run_mysql.py
│   └── __keep__.txt
├── models/
├── reports/
├── requirements.txt
├── scripts/
└── visualizations/
```
│   ├── admin.py
│   ├── api_urls.py
│   ├── api_views.py
│   ├── ml/
│   ├── models.py
│   ├── serializers.py
│   ├── static/
│   ├── templates/
│   ├── urls.py
│   ├── utils.py
│   └── views.py
    |-- Flight/                 # Django project configuration package
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── docs/                   # Project documentation and notes
├── manage.py               # Django management entry point
├── README.md               # Project documentation
├── requirements.txt        # Python dependencies
├── run.bat                 # Windows startup helper
├── run_mysql.py            # Simple startup helper
└── __keep__.txt            # Placeholder file
```

## Using the app

1. Register a new account or login.
2. Navigate to the prediction screen.
3. Enter route details and travel date.
4. Review the predicted price, general fare average, and live market signal note.

## Notes

- The app currently uses fallback logic for the live market signal.
- If you want to enable a live API in the future, update the API configuration and the `_get_live_price_signal` logic in `FlightPrice/views.py`.

## Troubleshooting

- If the server fails to start, verify you are running commands from the project root where `manage.py` exists.
- If dependencies are missing, run:

```bash
pip install -r requirements.txt
```

- If MySQL is not accessible, either install/configure MySQL or switch to a compatible SQLite settings file if available.

## Useful commands

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
python run_mysql.py
```

## Dependencies

The project dependencies are declared in `requirements.txt`, including:

- Django 6.0.7
- djangorestframework
- numpy
- pandas
- matplotlib
- scikit-learn
- seaborn
- mysqlclient
- python-dotenv
- xgboost
- lightgbm

## Contact

For help, inspect Django logs and confirm the database configuration in `Flight/settings.py`.
