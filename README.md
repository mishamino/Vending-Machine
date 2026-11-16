
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

## Online database and hosting

The settings support a MySQL database through the `DATABASE_URL` environment
variable. For the optional MySQL driver, install:

```powershell
python -m pip install -r requirements-online.txt
```

An online provider/database has not been configured or tested. Hosting still
requires a provider, a database created there, private environment settings
for `DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, and
`DJANGO_ALLOWED_HOSTS`, applying migrations, moving verified data, and following
the provider's production WSGI and static-file instructions. Do not put
production passwords or keys in source files.

## Learning reference

The primary learning reference is the
[W3Schools Django tutorial](https://www.w3schools.com/django/). Read its
project/app, views, URLs, templates, models, and CRUD lessons, then follow a
request through this project's URL, view, model, and template or JSON response.

# Vending-Machine
A Django-based vending machine web application with SQL database integration, payment processing, and denomination tracking.

