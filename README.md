# FlightPrice Prediction Project

A Django-based flight price prediction application that combines historical fare data, machine learning forecasts, and route-level market summaries.

## What this project does

- Supports user registration and login
- Uses historical route and fare data for baseline pricing
- Predicts route/date-specific fares with machine learning
- Displays prediction output together with a summary note
- Includes admin reporting, dataset overview, and model training features

## Key behavior

- **General Price** is the historical average fare for a selected route.
- **Forecasted fare** is the route/date-specific machine learning estimate.
- **Live Market Signal** is currently a summary note and not a live API fetch.

## Requirements

- Python 3.11+ (recommended)
- MySQL server for the default database backend
- `pip` for installing dependencies

## Install

From the repository root (`FlightPrice`):

```bash
pip install -r requirements.txt
```

## Setup

1. Create the MySQL database and user if required.
2. Update the database settings in `Flight/settings.py`.
3. Run Django migrations:

```bash
python manage.py migrate
```

## Run the app

From the repository root:

```bash
python manage.py runserver 8000
```

Or use the included helper:

```bash
python run_mysql.py
```

Then open:

```
http://127.0.0.1:8000/
```

## Repository structure

This repository contains one Django project and one Django app package.

```
FlightPrice/                # repo root
├── .env                    # local environment variables (ignored)
├── .gitignore
├── .venv/                  # Python virtual environment (ignored)
├── catboost_info/          # local training artifacts (ignored)
├── docs/
├── Flight/                 # Django project package
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── FlightPrice/            # main Django app package
│   ├── __init__.py
│   ├── admin.py
│   ├── api_urls.py
│   ├── api_views.py
│   ├── management/
│   ├── migrations/
│   ├── ml/
│   ├── models/
│   ├── models.py
│   ├── serializers.py
│   ├── static/
│   ├── templates/
│   ├── tests/
│   ├── tests.py
│   ├── urls.py
│   ├── utils.py
│   └── views.py
├── manage.py
├── README.md
├── requirements.txt
├── run.bat
├── run_mysql.py
└── __keep__.txt
```

## Using the app

1. Register a new account or login.
2. Open the prediction page.
3. Enter a route and travel date.
4. Review the forecasted price, historical average, and market note.

## Notes

- `.env` is used for local configuration and is ignored by Git.
- `Flight/settings.py` holds the database and application settings.
- `catboost_info/` and generated model files are ignored to keep the repository clean.

## Troubleshooting

- Run commands from the repository root where `manage.py` is located.
- If dependencies are missing:

```bash
pip install -r requirements.txt
```

- If MySQL is not accessible, update `Flight/settings.py` with a compatible local database configuration.

## Useful commands

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
python run_mysql.py
```

## Dependencies

Dependencies are declared in `requirements.txt` and include:

- Django
- djangorestframework
- numpy
- pandas
- scipy
- scikit-learn
- joblib
- threadpoolctl
- matplotlib
- seaborn
- xgboost
- lightgbm
- catboost
- mysqlclient
- python-dotenv
- python-dateutil
- pytz
- tzdata

## Contact

For help, inspect Django logs and confirm the database configuration in `Flight/settings.py`.
