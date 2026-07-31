# Installation Guide

## Prerequisites

- Python 3.11+ or Python 3.12
- MySQL Server
- Git (optional)
- Virtual environment tool such as `venv`

## Setup Steps

1. Clone the repository:

```bash
cd C:\Users\laksh\OneDrive\Desktop\FlightPrice\FlightPrice
```

2. Create and activate a Python virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Configure the database:

- Create a MySQL database named `FlightPrice` or update `.env` values.
- Ensure MySQL credentials match `Flight/settings.py` or environment variables.

5. Run Django migrations:

```powershell
python manage.py migrate
```

6. Prepare the dataset:

- The dataset CSV is available at `Dataset/FlightPrice.csv`.
- The application loads this CSV for training and predictions.

7. Start the application locally:

```powershell
python run_mysql.py
```

8. Open the browser:

```text
http://127.0.0.1:8001/
```

## Notes

- `requirements.txt` contains pinned package versions.
- If any package fails to install, upgrade `pip` first:

```powershell
python -m pip install --upgrade pip
```
