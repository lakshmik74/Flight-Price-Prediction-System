# Model Documentation

## Overview

The FlightPrice ML pipeline trains regression models on historical flight pricing data to predict future ticket fares. It includes automated dataset loading, feature engineering, label encoding, scaling, candidate model evaluation, model selection, and artifact persistence.

## Model Pipeline Components

### Dataset loading

- Located in `FlightPrice/ml/data.py`
- Loads `FlightPrice.csv` from one of these locations:
  - `data/raw/FlightPrice.csv`
  - `Dataset/FlightPrice.csv`
  - `FlightPrice/Dataset/FlightPrice.csv`

### Feature engineering

- Located in `FlightPrice/ml/features.py`
- Converts raw columns into numeric features:
  - `Date_of_Journey` → `day`, `month`, `year`, `day_of_week`
  - `Dep_Time` → `dep_hour`, `dep_minute`
  - `Arrival_Time` → `arrival_hour`, `arrival_minute`
  - `Duration` → `duration_minutes`
  - `Total_Stops` → `Total_Stops`
  - `Additional_Info` cleaned and normalized
- Drops unused columns such as `Date_of_Journey`, `Dep_Time`, `Arrival_Time`, `Duration`, `Route`

### Encoding and scaling

- Label encoding is applied to categorical columns:
  - `Airline`
  - `Source`
  - `Destination`
  - `Additional_Info`
- Min-max scaling is applied to numeric feature vectors.

### Candidate models

Supported candidate regressors:

- Random Forest (`RandomForestRegressor`)
- Decision Tree (`DecisionTreeRegressor`)
- Linear Regression (`LinearRegression`)
- Gradient Boosting (`GradientBoostingRegressor`)
- XGBoost (`XGBRegressor`) if installed
- LightGBM (`LGBMRegressor`) if installed
- CatBoost (`CatBoostRegressor`) if installed

### Training and evaluation

- The training pipeline is defined in `FlightPrice/ml/model.py`.
- The best model is selected based on RMSE and validation performance.
- Metrics saved in `reports/model_comparison.json` include:
  - `rmse`
  - `mae`
  - `r2`
- The best model is persisted to `models/production_model.joblib`.

### Prediction

- Prediction entrypoint is `FlightPrice/ml/model.py:predict_price()`.
- Predictions use the latest production model or best evaluated model.
- The function accepts:
  - `airline`
  - `source`
  - `destination`
  - `day`
  - `month`
  - `year`
- Output includes `prediction`, `general_price`, and `selected_model`.

## Artifact layout

- `models/production_model.joblib` — Active production model artifact
- `models/best_model.joblib` — Best evaluated candidate model artifact
- `models/scaler.joblib` — Saved scaler for input normalization
- `models/model_metadata.joblib` — Metadata for current model and dataset
- `reports/model_comparison.json` — Comparison metrics and best model details
- `reports/model_comparison.md` — Markdown report for model comparison
- `reports/model_comparison.pdf` — PDF summary of model comparison
- `reports/eda_summary.*` — Exploratory data analysis artifacts
- `reports/feature_engineering.md` — Feature engineering documentation

## Model Versioning

- The project supports model artifact versioning in `models/`.
- Models are normalized using names like `v1_random_forest.joblib`.
- `train_pipeline()` returns version metadata for tracking.

## Performance notes

- The project emphasizes explainability and a strong administrative workflow for model promotion, rollback, and artifact management.
- Production quality is improved by saving human-readable reports and PDF exports.
