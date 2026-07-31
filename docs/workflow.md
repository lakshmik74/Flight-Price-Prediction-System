# Workflow Diagram

## User Workflow

1. User visits the web application
2. User registers or logs in
3. User opens the dashboard or admin panel
4. User submits route details on the prediction page
5. System validates input and generates a price prediction
6. Prediction history is saved and reports may be generated

## Admin Workflow

1. Admin logs in to `AdminPanel`
2. Admin can upload a new dataset or retrain the model
3. System runs the training pipeline and evaluates candidate models
4. Model comparison reports are generated in `reports/`
5. Admin can promote a model to production or rollback a previous version
6. Users continue making predictions using the active production model

## API Workflow

1. Client calls `/api/predict/` with route and date parameters
2. API validates request using `PredictionSerializer`
3. Prediction engine loads the production model
4. Model returns prediction results
5. API returns JSON payload containing prediction details

## Machine Learning Workflow Diagram

```
Raw Dataset
  └─> Data Cleaning
         └─> EDA
                └─> Feature Engineering
                       └─> Model Training
                              └─> Hyperparameter Tuning
                                     └─> Model Evaluation
                                            └─> Best Model Selection
                                                   └─> Model Deployment
                                                          └─> Prediction
                                                                 └─> Live API Comparison
                                                                        └─> Analytics Dashboard
```

## ML Training Workflow

1. Load raw dataset from `Dataset/FlightPrice.csv`
2. Process raw features via `ml/features.py`
3. Encode categorical values and scale inputs
4. Train candidate regressors
5. Compare model metrics and select the best model
6. Save the production artifact and generate reports

## Feature Engineering Diagram (Textual)

```
Raw CSV data -> load_dataset() -> prepare_feature_frame()
      -> label encoding -> scaling -> model training
      -> artifact save -> report generation
```

## Reporting Workflow

1. Training pipeline stores metrics in JSON and Markdown files
2. PDF summaries are created with `matplotlib.backends.backend_pdf.PdfPages`
3. Admin dashboard surfaces report download links
4. Reports are used for model monitoring and comparison
