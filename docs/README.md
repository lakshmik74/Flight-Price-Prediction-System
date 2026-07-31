# FlightPrice Prediction Project

FlightPrice is a Django-based web application for flight fare prediction using machine learning. It combines data ingestion, dataset preparation, model training, model monitoring, administrative workflows, and REST API support.

## Project Goals

- Predict flight prices with historical airline and route data
- Generate professional reports for EDA, feature engineering, model comparison, and prediction monitoring
- Provide admin workflows for retraining, model promotion/rollback, artifact downloads, and dataset uploads
- Expose REST API endpoints for predictions, model metadata, health checks, and retraining

## Contents

- `Flight/` — Django project configuration and settings
- `FlightPrice/` — Django app containing ML utilities, views, models, templates, admin workflows, and REST APIs
- `Dataset/` — Flight pricing data source (`FlightPrice.csv`)
- `requirements.txt` — Python dependencies
- `run_mysql.py` — MySQL-based run helper script
- `manage.py` — Django CLI entry point
- `docs/` — Project documentation
- `reports/` — Generated report artifacts
- `models/` — Persisted ML model and preprocessing artifacts

## Documentation Files

- `docs/README.md` — Project overview and documentation index
- `docs/installation.md` — Install and local setup guide
- `docs/deployment.md` — Production deployment guidance
- `docs/api.md` — REST API documentation
- `docs/model.md` — Machine learning pipeline and model documentation
- `docs/dataset.md` — Dataset details and data dictionary
- `docs/architecture.md` — Architecture description and diagrams
- `docs/workflow.md` — Workflow diagrams and feature flow descriptions
- `docs/testing.md` — Testing strategy and coverage guidance
