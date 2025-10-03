# Client Time Tracking Web App/API

## Overview

**Time Tracker** is a self‑hosted web application that lets a single user track
work tickets, manage a simple client list and keep an inventory of hardware.
The project provides both a browser‑based UI and a headless JSON API, built on
FastAPI with SQLAlchemy ORM and Jinja2 templates.  A default SQLite database
stores data, and Docker Compose makes it easy to run everything locally.

### Features

* **Ticket tracking** – Create, view, update and delete support tickets.  Each
  ticket tracks description, client information, and completion status.
* **Hardware inventory** – Maintain an inventory of hardware items with a
  unique barcode, description, acquisition cost and sales price.
* **Client list** – Load and display a list of clients from a JSON file
  (`client_table.json`).
* **USPS-verified address autocomplete** – Client address fields can be
  auto-completed with USPS-certified suggestions when SmartyStreets
  credentials are provided.
* **Responsive UI** – HTML pages served with Jinja2 templates and static
  resources provide a simple front‑end for managing tickets, hardware and
  clients.  Sessions and login keep your changes protected.
* **RESTful API** – The same CRUD actions are exposed over a versioned API
  (`/api/v1/…`) for programmatic access.  An `X‑API‑Key` header protects
  endpoints when an API token is configured.
* **Simple authentication** – A single user can log in via the browser UI.
  API requests are authenticated with a bearer token header when enabled.
* **Docker deployment** – A `docker-compose.yml` file builds the app and
  manages a persistent data volume.  Environment variables control all
  secrets and options.

## Architecture

The application uses FastAPI as its web framework and SQLAlchemy for the ORM.
Data is persisted in a SQLite database by default (`/data/data.db`), with
migrations handled at startup.  UI pages live under `app/templates/` and
`app/static/`, while API and UI routes live in `app/routers/`.  Business logic
is encapsulated in `app/crud/` modules and the database models are defined
in `app/models/`.

Authentication for the UI is configured via environment variables
(`UI_USERNAME`, `UI_PASSWORD` or a bcrypt `UI_PASSWORD_HASH`).  API requests
use an optional `API_TOKEN` specified in the environment and passed via the
`X‑API‑Key` header.

## Quick start with Docker Compose

1. **Clone the repository**:

   ```sh
   git clone https://github.com/aarnt28/time-tracker4-refactored.git
   cd time-tracker4-refactored
   ```

2. **Create a `.env` file** (optional) – copy from `.env.example` (if provided)
   and customise `API_TOKEN`, UI credentials and other settings.

3. **Start the stack**:

   ```sh
   docker compose up -d
   ```

   This builds the container, creates a persistent `data/` volume and
   publishes the web app on port `8089` (see `docker-compose.yml` to change
   ports).  Visit [http://localhost:8089/](http://localhost:8089/) in your
   browser to log in and begin using the UI.  API endpoints are available
   under `/api/v1/`.

## Running locally (without Docker)

If you prefer not to use Docker you can run the app directly with Python.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export API_TOKEN="your-token-here"
export UI_USERNAME="admin"
export UI_PASSWORD="change-me"
uvicorn app:app --reload --host 0.0.0.0 --port 8089
```

By default a SQLite database will be created in `data/data.db`.  Set
`DB_URL` in your environment to point at another database if required.

## API usage

When `API_TOKEN` is set, all routes under `/api/v1/` require a matching
`X‑API‑Key` header.  Example requests are shown below:

### Create a hardware item

```http
POST /api/v1/hardware HTTP/1.1
Host: tracker.example.com
X-API-Key: your-token
Content-Type: application/json

{
  "barcode": "12345",
  "description": "Router",
  "acquisition_cost": "29.99",
  "sales_price": "49.99"
}
```

### List hardware

```http
GET /api/v1/hardware?limit=100&offset=0 HTTP/1.1
Host: tracker.example.com
X-API-Key: your-token
```

Similar endpoints exist for tickets (`/api/v1/tickets`) with standard CRUD
operations.  See `app/routers/api_hardware.py` and `app/routers/api_tickets.py`
for implementation details.

## Configuration

The application reads configuration from environment variables defined in
`app/core/config.py`.  Key settings include:

| Variable            | Description                                | Default              |
|---------------------|--------------------------------------------|----------------------|
| `API_TOKEN`         | API key required via `X‑API‑Key` header     | empty (disabled)     |
| `APP_SECRET`        | Secret key for session cookies              | `dev-insecure-secret-change-me` |
| `UI_USERNAME`       | Username for the browser UI                 | `admin`              |
| `UI_PASSWORD`       | Password for the browser UI (plaintext)     | `change-me`          |
| `UI_PASSWORD_HASH`  | Bcrypt hash of the UI password (takes precedence) | empty                |
| `DB_URL`            | SQLAlchemy database URL                    | `sqlite:///data.db`  |
| `TZ`                | Time zone for timestamps                    | `America/Chicago`    |
| `SESSION_COOKIE_NAME` | Name of the session cookie                | `tt_session`         |
| `SESSION_MAX_AGE`   | Session lifetime in seconds                 | `2592000` (30 days)  |
| `SMARTY_AUTH_ID`    | SmartyStreets Auth ID for USPS address APIs | empty (disabled)     |
| `SMARTY_AUTH_TOKEN` | SmartyStreets Auth Token                    | empty (disabled)     |
| `SMARTY_AUTOCOMPLETE_URL` | Override for the autocomplete endpoint | Smarty default       |
| `SMARTY_STREET_URL` | Override for the verification endpoint      | Smarty default       |

Refer to `app/core/config.py` and `docker-compose.yml` for the full list of
environment variables and their defaults.

### Address autocomplete setup

Address prefill in the client editor is powered by SmartyStreets' USPS-certified
APIs. To enable it:

1. Create a (free) SmartyStreets account and generate an **Auth ID** and
   **Auth Token** for the US Autocomplete Pro and US Street APIs.
2. Set the `SMARTY_AUTH_ID` and `SMARTY_AUTH_TOKEN` environment variables for
   the application (for example in `.env` or your Docker Compose file).
3. Restart the application. When editing a client, typing into **Address Line 1**
   will display USPS-verified suggestions. Selecting a suggestion automatically
   fills the remaining city/state/ZIP fields after verification.

If the credentials are omitted, the UI silently falls back to manual entry.

## Contributing

This project currently targets a single-user workflow.  Future enhancements
might include multi-user support, more granular permissions, richer client
management and improved reporting.  Pull requests are welcome!  Please
ensure new code is well-tested and keep changes focused on a single purpose.

## License

Include the appropriate license information here if one exists.  Otherwise,
replace this section or remove it as needed.
