# Deployment Guide

## Deployment Goals

This guide covers how to deploy the FlightPrice application in a production-like environment with a reliable database backend and static asset serving.

## Recommended Production Stack

- Python 3.11+ / 3.12
- MySQL 8.x
- Gunicorn or uWSGI
- Nginx for reverse proxy and static file serving
- Windows Server or Linux server

## Production Configuration

1. Use environment variables for secrets and database credentials.
   - `DB_NAME`
   - `DB_USER`
   - `DB_PASSWORD`
   - `DB_HOST`
   - `DB_PORT`
   - `SECRET_KEY`
   - `DEBUG=False`

2. Configure `Flight/settings.py` to read from `.env` or environment variables.

## Deployment Steps

1. Install Python and MySQL on the target server.
2. Clone the repository to the deployment host.
3. Create a Python virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate    # Windows
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Set environment variables or create a `.env` file.

6. Run database migrations:

```bash
python manage.py migrate
```

7. Collect static assets:

```bash
python manage.py collectstatic --noinput
```

8. Configure a process manager:

### Gunicorn example (Linux)

```bash
gunicorn Flight.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

### uWSGI example

```bash
uwsgi --http :8000 --module Flight.wsgi:application --master --processes 4 --threads 2
```

9. Configure Nginx as a reverse proxy:

```nginx
server {
    listen 80;
    server_name example.com;

    location /static/ {
        alias /path/to/FlightPrice/FlightPrice/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Security and Maintenance

- Set `DEBUG = False` in production.
- Restrict allowed hosts in `ALLOWED_HOSTS`.
- Use HTTPS/TLS.
- Monitor log files and database health.

## Backup Strategy

- Regularly back up the MySQL database.
- Archive `models/` and `reports/` if models are updated.
- Preserve `Dataset/FlightPrice.csv` and any uploaded datasets.
