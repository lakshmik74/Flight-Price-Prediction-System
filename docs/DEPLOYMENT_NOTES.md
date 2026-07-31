Deployment notes — FlightPrice runtime changes

Overview

- This project now uses the `FlightPrice` package directly. The legacy `FlightFare` compatibility shim has been removed, and all imports should reference `FlightPrice.*`.

What to update in deployments

1) Python path / virtualenv
- Ensure your deployment points to the project root (the folder that contains `manage.py`).
- Activate or reference the same venv used for development.
  Example systemd ExecStart for Gunicorn:

  /path/to/venv/bin/gunicorn Flight.wsgi:application --bind 0.0.0.0:8000 --chdir /path/to/FlightPrice/FlightPrice

- For Windows services / Task Scheduler, set `Start in` to the project directory and run the venv Python executable.

2) WSGI / Gunicorn / uWSGI
- No change required to `DJANGO_SETTINGS_MODULE` (`Flight.settings`) or `WSGI_APPLICATION`.
- Confirm your `--chdir` or working directory points at the project directory that contains `manage.py`.

3) Systemd example (Linux)

[Unit]
Description=Gunicorn instance to serve Flight project
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/flightproject/FlightPrice/FlightPrice
Environment="PATH=/srv/flightproject/.venv/bin"
ExecStart=/srv/flightproject/.venv/bin/gunicorn Flight.wsgi:application --workers 3 --bind unix:/run/flight.sock

[Install]
WantedBy=multi-user.target

- After editing: `sudo systemctl daemon-reload && sudo systemctl restart flight`.

4) Windows Task Scheduler / Service notes
- Use the full path to the venv Python as the `Program/script` and set `Start in` to the project folder.
- Example action arguments: `C:\path\to\FlightPrice\FlightPrice\manage.py runserver 0.0.0.0:8000` (for dev) or call a service wrapper for production.

5) Scripts & CI
- Ensure your CI and automation scripts import directly from `FlightPrice.*`.
- Update any PATH or file paths in deployment scripts that referenced the old shim or package names if those paths are used literally.

6) Editor / Pylance
- Ensure the remote/production Python interpreter matches the venv used in development if you want consistent Pylance/linting behavior.
- If Pylance shows missing imports, ensure the venv is selected in VS Code (`Python: Select Interpreter`) and restart the window.

7) How to revert or perform a full app rename later
- A full app rename requires changing the app package name and migrations/app labels. Steps (high-level):
  1. Backup the DB.
  2. Create a new app package with the desired name.
  3. Move models and adjust `apps.py` and `INSTALLED_APPS`.
  4. Create new migrations and run data migrations to copy content if needed, or use `migrate --fake` carefully.
  5. Update all imports and scripts.
- This is non-trivial and can break historical migrations — do it only if you need the app label changed in the DB.

Quick checks after deployment changes

- `cd /path/to/project && /path/to/venv/bin/python manage.py check`
- Run representative tests: `./venv/bin/python manage.py test FlightPrice.tests.AdminPanelTests.test_admin_panel_renders_for_authenticated_user`.
- Restart your application server and inspect logs for import errors.

Contact me if you want me to generate modified systemd unit files or CI snippets tailored to your deployment environment.
