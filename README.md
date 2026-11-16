
# Ebene Campus Vending Machine - Django

This is a Django web application that simulates the physical vending machine
at Ebene Campus. It is a local machine simulation, not an online shop.

The project follows the beginner Django concepts in the W3Schools tutorial:
project and app structure, URL patterns, views, templates, models, forms, and
database-backed create/read/update/delete actions.

## Project structure

- `manage.py` runs Django commands.
- `vending_site/settings.py` configures Django, templates, static files,
  authentication, time zone, and database connection.
- `vending_site/urls.py` connects the site URLs to Django views.
- `vending/models.py` describes products and the transaction tables.
- `vending/views.py` handles machine actions and inventory pages.
- `vending/forms.py` checks product and restock input.
- `vending/urls.py` lists the vending app URLs.
- `vending/migrations/` contains Django's database schema instructions.
- `templates/` contains Django HTML templates.
- `static/` contains CSS, JavaScript, and product images.
- `vending/tests.py` tests the main vending behavior.
- `db.sqlite3` is the local Django database and includes the current product
  and transaction records.
- `build.sh` installs production dependencies, collects static files, and
  applies database migrations for Render.
- `render.yaml` describes the Render web service.

## Run on Windows

Open PowerShell in this project folder. To make a clean Python environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py createsuperuser  # run once to create the inventory account
python manage.py runserver
```

Open the machine at `http://127.0.0.1:8000/`. Sign in at
`http://127.0.0.1:8000/admin/login/` and open stock management at
`http://127.0.0.1:8000/admin/`. Select **Transaction History** in the dashboard
to view every recorded transaction, including pending transactions, in a
paginated list. The built-in Django administration site is at
`http://127.0.0.1:8000/django-admin/`.

The included `db.sqlite3` already has the project data. Do not delete it if you
want to keep that data. `createsuperuser` makes a Django account for the admin
pages; its password is saved as a secure hash by Django.

## Local database and Big Data records

Local development uses SQLite in `db.sqlite3`, in this project folder. Django
models describe the tables, and Django migrations create their structure.

- `vending_product` stores product details and remaining quantity.
- `vending_vendingtransaction` stores the date, time, status, and money totals.
- `vending_transactioninsertion` stores one row for each inserted coin or note.
- `vending_transactionitem` stores each successful product selection.
- `vending_transactionchange` stores one row for each returned coin or note.

Money is stored as integer cents to avoid rounding errors. When a purchase
succeeds, the application updates stock and saves its item record together in
a database transaction. Invalid purchases do not create sale records or reduce
stock.

## Deploy on Render

The project keeps SQLite as its local default and uses PostgreSQL whenever
`DATABASE_URL` is set. The production database URL, Django secret key, and
allowed hosts are read from environment variables. WhiteNoise serves the
collected static files; the application runs under Gunicorn.

1. Create a Render PostgreSQL database and a Render web service from this
   repository, using the included Blueprint or the commands below. Set the
   web service's `DATABASE_URL` to the database's **internal** URL; keep it in
   Render's environment settings, not in source control.
2. Set `DJANGO_SECRET_KEY` to a generated secret and `DJANGO_DEBUG` to `false`.
   Set `DJANGO_ALLOWED_HOSTS` to the Render hostname (and any custom domains,
   comma-separated). Render also supplies `RENDER_EXTERNAL_HOSTNAME`, which
   the settings add to the allowed hosts.
3. Let the Render build run migrations and collect static files. Create a
   staff account once from the Render Shell with
   `python manage.py createsuperuser`.
4. To carry over the existing SQLite products and transactions, first verify
   that `db.sqlite3` and its `db.sqlite3.backup` copy are intact. On the local
   machine, with the local SQLite database selected, export the vending app's
   data:

   ```powershell
   python manage.py dumpdata vending --indent 2 --output vending-data.json
   ```

   This fixture contains products, vending transactions, each inserted
   denomination, each purchased item, and each returned-change denomination,
   retaining primary keys and foreign-key relationships. Keep it private and
   do not commit it. Once the Render PostgreSQL schema has been created by the
   build, run `python manage.py loaddata vending-data.json` with `DATABASE_URL`
   set to the database's **external** URL in the local process environment.
   On Windows PowerShell, this prompts for the external URL without echoing it
   or placing it in command history:

   ```powershell
   $secureUrl = Read-Host "Render PostgreSQL external URL" -AsSecureString
   $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureUrl)
   try {
       $env:DATABASE_URL = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
       $env:DJANGO_DEBUG = "false"
       $env:DJANGO_SECRET_KEY = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
       python manage.py loaddata vending-data.json
   } finally {
       Remove-Item Env:DATABASE_URL,Env:DJANGO_DEBUG,Env:DJANGO_SECRET_KEY -ErrorAction SilentlyContinue
       [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
   }
   ```

   Do not load it into the Render internal URL from a local machine; that URL
   is only reachable by Render services. Alternatively, securely transfer the
   fixture to a Render Shell and load it there using the service's internal
   `DATABASE_URL`. Do not repeat the import into a database that already has
   these records.

The local database was preserved and backed up before deployment changes:
`db.sqlite3.backup` is an ignored, verified copy of `db.sqlite3`. At backup
time, both copies passed SQLite's integrity check and held 22 products, 11
transactions, 31 inserted-denomination records, 15 transaction-item records,
and 35 returned-change records.

### Render commands and environment

The included `render.yaml` uses the following commands:

- **Build:** `bash build.sh`
- **Start:** `gunicorn vending_site.wsgi:application`

`build.sh` installs `requirements.txt`, runs `collectstatic --no-input`, and
applies migrations. For a manually created Render service, use those commands
as its build and start commands.

Configure these environment variables in Render:

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | Render PostgreSQL internal URL (secret; do not commit it) |
| `DJANGO_SECRET_KEY` | Generated private Django secret |
| `DJANGO_DEBUG` | `false` |
| `DJANGO_ALLOWED_HOSTS` | Render service host and custom domains, comma-separated |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Optional HTTPS origins for additional custom domains |

`RENDER_EXTERNAL_HOSTNAME` is supplied by Render and is also added to
`ALLOWED_HOSTS`. Leave `DATABASE_URL` unset locally to use `db.sqlite3`. The
included Blueprint prompts for the PostgreSQL URL instead of storing a
credential in `render.yaml`. Choose a PostgreSQL plan appropriate for
persistent production data; verify the provider's backup and retention policy
before relying on it.

No live Render service or PostgreSQL database has been provisioned or tested
from this project workspace.

## Learning reference

The primary learning reference is the
[W3Schools Django tutorial](https://www.w3schools.com/django/). Read its
project/app, views, URLs, templates, models, and CRUD lessons, then follow a
request through this project's URL, view, model, and template or JSON response.

# Vending-Machine
A Django-based vending machine web application with SQL database integration, payment processing, and denomination tracking.
