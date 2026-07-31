# API Documentation

## Overview

This project exposes REST API endpoints under `/api/` for prediction, model metadata, retraining, and health checks.

## Base URL

`http://<host>:<port>/api/`

## Endpoints

### GET /api/health/

Returns simple health information.

Response:

```json
{
  "success": true,
  "status": "healthy",
  "models_available": 2,
  "report_available": true
}
```

### POST /api/predict/

Submit a prediction request.

Request body:

```json
{
  "airline": "Air India",
  "source": "Delhi",
  "destination": "Mumbai",
  "day": 10,
  "month": 10,
  "year": 2025
}
```

Response:

```json
{
  "success": true,
  "data": {
    "prediction": 1234.56,
    "general_price": 1200.0,
    "selected_model": "random_forest",
    "model_version": "v3_random_forest"
  }
}
```

### GET /api/models/

Returns a list of persisted model artifacts.

Response:

```json
{
  "success": true,
  "models": [
    {
      "name": "production_model.joblib",
      "size_kb": 231.45,
      "modified_at": 1710000000.0
    }
  ]
}
```

### GET /api/history/

Returns retraining history records.

Response:

```json
{
  "success": true,
  "results": [
    {
      "model_name": "random_forest",
      "model_version": "v5_random_forest",
      "dataset_version": "FlightPrice.csv@1710000000",
      "training_date": "2026-07-20T12:34:56Z",
      "rmse": 123.45,
      "mae": 95.67,
      "training_time_seconds": 12.34,
      "model_path": "models/v5_random_forest.joblib",
      "is_production": true
    }
  ]
}
```

### GET /api/model-performance/

Returns the latest model comparison report.

Response:

```json
{
  "success": true,
  "performance": {
    "rows": 10000,
    "features": ["Airline", "Source", "Destination", "day", "month", "year"],
    "models_evaluated": [
      {
        "name": "random_forest",
        "model_version": "v5_random_forest",
        "rmse": 120.5,
        "mae": 90.1,
        "r2": 0.87
      }
    ],
    "best_model": {
      "name": "random_forest",
      "model_version": "v5_random_forest",
      "rmse": 120.5,
      "mae": 90.1,
      "r2": 0.87
    },
    "notes": "Model comparison generated from latest retraining run."
  }
}
```

### POST /api/retrain/

Triggers retraining of the ML pipeline.

Request body: none

Response:

```json
{
  "success": true,
  "message": "Retraining completed.",
  "data": {
    "best_model": "random_forest",
    "rmse": 120.5,
    "mae": 90.1,
    "r2": 0.87,
    "model_version": "v5_random_forest"
  }
}
```

## Authentication

- `/api/retrain/` requires a valid authenticated session.
- `/api/predict/`, `/api/models/`, `/api/history/`, `/api/model-performance/`, and `/api/health/` are publicly accessible.

## Notes

- Endpoint URLs are served by `FlightPrice/api_urls.py`.
- Serializers are defined in `FlightPrice/serializers.py`.
- The API is built using Django REST Framework.
