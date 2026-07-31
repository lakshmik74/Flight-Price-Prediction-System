# Architecture Diagram

## System Overview

FlightPrice follows a standard Django MVC architecture with extended machine learning and reporting capabilities.

## Components

- `Flight/` — Django project configuration, URL routing, and WSGI app entry point
- `FlightPrice/` — Django application with views, models, serializers, REST API endpoints, ML utilities, templates, and static content
- `Dataset/` — Raw data source used for training and analysis
- `models/` — Persisted machine learning artifacts
- `reports/` — Generated reports and PDF/Markdown exports

## Logical Architecture

1. User Interface
   - HTML templates served by Django views
   - Admin panel for model management
   - Prediction form for fare estimation

2. Business Logic
   - `views.py` handles request routing and rendering
   - `models.py` defines Django ORM models for user signup, prediction history, and retraining history
   - `utils.py` contains helper functions and table initialization logic

3. Machine Learning Layer
   - `ml/data.py` loads and caches the dataset
   - `ml/features.py` transforms raw dataset columns into machine learning features
   - `ml/model.py` trains candidate models, evaluates metrics, saves artifacts, and exposes prediction APIs

4. REST API Layer
   - `api_urls.py` registers API routes
   - `api_views.py` implements prediction, model listing, history, performance, retraining, and health endpoints
   - `serializers.py` validates API request and response payloads

5. Persistence
   - Django ORM models stored in MySQL
   - Model artifacts saved to disk as `.joblib`
   - Reports saved as `.json`, `.md`, `.pdf`

## System Architecture Diagram

```
User
  └─> Django Frontend
         ├─> Authentication
         ├─> Prediction Service
         │       ├─> Preprocessing Pipeline
         │       │       ├─> Raw Dataset
         │       │       ├─> Data Cleaning
         │       │       └─> Feature Engineering
         │       ├─> Machine Learning Models
         │       └─> Live Flight API
         ├─> Database
         └─> Analytics Dashboard
```

## Architecture Diagram (Textual)

```
User Browser
     |
     | HTTP requests
     v
Django Views (FlightPrice/views.py)
     |\
     | \-- renders templates (index, PredictPrices, AdminPanel, Dashboard)
     |  \
     |   \-- HTTP API endpoints (/api/)
     v
Business Logic + ML
     |
     |-- dataset loading (ml/data.py)
     |-- feature engineering (ml/features.py)
     |-- model training & evaluation (ml/model.py)
     |-- report generation (reports/)
     v
Persistence
     |-- MySQL database
     |-- Artifact storage (models/*.joblib)
     |-- Report storage (reports/*.json, *.md, *.pdf)
```

## Deployment Diagram

```
[Client] <--HTTPS--> [Nginx/Proxy] <--HTTP--> [Django App Server]
                                        |
                                        +-- [MySQL Database]
                                        |
                                        +-- [File Storage: models/, reports/, Dataset/]
```

## Notes

- The ML layer is designed to be reusable from the web app and API.
- The application can be extended with external APIs for live price signals.
- Reports are generated automatically during model training and prediction history updates.
