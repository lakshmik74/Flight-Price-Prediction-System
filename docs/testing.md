# Testing

This project includes a broad test strategy across unit, integration, API, model, authentication, and coverage reporting.

## Test Types

### Unit Tests
- Validate individual functions and classes.
- Focus areas include:
  - `views.py` helper logic and response formatting
  - `ml/data.py` dataset loading
  - `ml/features.py` preprocessing transformations
  - `serializers.py` request validation
  - report generation functions in `ml/model.py`

### Integration Tests
- Validate multiple layers working together.
- Use Django `Client` and `RequestFactory` to perform request flows.
- Examples in `FlightPrice/FlightPrice/FlightPrice/tests.py`:
  - admin panel access control
  - retrain workflow
  - artifact download endpoints
  - model promotion/rollback flows

### API Tests
- Validate REST API endpoints under `/api/`.
- Ensure correct payload validation and response structure.
- Covered endpoints:
  - `POST /api/predict/`
  - `GET /api/models/`
  - `GET /api/history/`
  - `GET /api/model-performance/`
  - `POST /api/retrain/`
  - `GET /api/health/`

### Model Tests
- Validate the machine learning pipeline and artifact persistence.
- Ensure training, model saving, and metadata logic execute correctly.
- Examples include:
  - `train_pipeline()` behavior
  - model comparison report generation
  - prediction result structure

### Authentication Tests
- Validate session-based login and route protection.
- Ensure protected admin and dashboard routes redirect unauthenticated users.
- Ensure authenticated users can access admin panel, model monitoring, and retrain actions.

## Running Tests

From the project root:

```powershell
python manage.py test
```

For a focused test module:

```powershell
python manage.py test FlightPrice.tests.PredictPricesActionTests --verbosity 2
```

## Coverage Report

Recommended coverage workflow:

```powershell
pip install coverage
coverage run --source=FlightPrice manage.py test
coverage report -m
coverage html
```

Open `htmlcov/index.html` in the browser to review coverage details.

## Notes

- Current test file: `FlightPrice/FlightPrice/FlightPrice/tests.py`
- The test suite uses Django `TestCase` and `TransactionTestCase` for proper isolation.
- Coverage should include all Python modules in `FlightPrice/` and the ML package.
