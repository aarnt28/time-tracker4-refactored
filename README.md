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
* **Ticket attachments** – Upload screenshots or other image files alongside
  a ticket for richer context directly from the UI or the API. Files are stored
  under the persistent data volume and exposed through secured download links.【F:app/routers/api_tickets.py†L15-L141】【F:app/templates/tickets.html†L302-L2115】
* **Invoice insights** – Tickets include invoiced totals and calculated value
  columns that auto-populate from hardware quantity × price or a client's
  rounded time × support rate, plus inline editing and sortable, hideable
  columns in the UI for flexible reporting.【F:app/crud/tickets.py†L18-L331】【F:app/templates/tickets.html†L224-L399】【F:app/templates/_rows.html†L1-L52】
* **Hardware inventory** – Maintain an inventory of hardware items with a
  unique barcode, description, acquisition cost and sales price.
* **Inventory adjustments & history** – Use the inventory dashboard to review
  on-hand counts, capture stock receipts/usage, and audit a chronological event
  log across all hardware.【F:app/templates/inventory.html†L24-L128】【F:app/routers/ui.py†L75-L166】
* **Automatic stock sync** – Hardware-linked tickets automatically create or
  update inventory usage events so every sale or install decrements stock
  without manual reconciliation.【F:app/crud/tickets.py†L105-L134】【F:app/crud/inventory.py†L89-L121】
* **Built-in barcode capture** – The hardware editor can scan barcodes using
  the browser camera (with a ZXing fallback) or an optional native bridge so
  serial numbers are populated without manual typing.
* **Client list** – Load and display a list of clients from a JSON file
  (`client_table.json`).
* **Custom client attributes** – Extend client records with bespoke fields and
  manage the allowed keys via the API, backed by `custom_attributes.json` on
  disk.【F:app/routers/clients.py†L20-L140】【F:app/services/custom_attributes.py†L24-L111】
* **Google address autocomplete & validation** – Client address fields are
  powered by Google Places Autocomplete and the Address Validation API, filling
  in city/state/ZIP details and coordinates when a Maps API key is configured.
* **Client location preview & overview map** – Display a pinned Google Map in
  the client editor and a consolidated map at the bottom of the Clients page
  that pins every mappable customer, making it easy to verify on-site details
  and plan visits at a glance.【F:app/templates/clients.html†L43-L60】【F:app/templates/clients.html†L250-L470】【F:app/templates/clients.html†L964-L1126】
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

### Inventory dashboard & stock workflow

The `/inventory` page surfaces three coordinated views: a stock summary grouped
by hardware item, a form to record receipts/usage, and a recent activity log so
you can spot anomalies at a glance.【F:app/templates/inventory.html†L24-L128】
Each submission posts back to `/inventory/adjust`, validates the quantity, and
persists an `inventory_events` record that captures the hardware id, signed
change, source (e.g. `ui:receive`) and optional note for auditing.【F:app/routers/ui.py†L75-L166】【F:app/models/inventory.py†L9-L34】
Aggregated counts are recalculated from those events every time the page loads
to reflect live balances.【F:app/crud/inventory.py†L22-L45】

Hardware tickets are kept in sync with the same event stream—creating or
updating a `hardware` entry ensures a matching usage event exists, while
switching back to a time entry removes it—so on-hand quantities stay accurate
without manual reconciliation.【F:app/crud/tickets.py†L105-L134】【F:app/crud/inventory.py†L89-L121】

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

## Headless API reference

The FastAPI application exposes every headless capability under the
`/api/v1/…` prefix.  Unless noted otherwise, callers must include an
`X‑API‑Key` header whose value matches `API_TOKEN`.  Interactive browser
sessions that are already logged in via the UI may call the same endpoints
without the header because the shared dependency accepts either an API key or
an authenticated UI session.【F:app/deps/auth.py†L1-L29】

The tables and examples below document every public, headless entry point and
its supported query parameters.  Example payloads illustrate typical responses;
fields that are `null` in the JSON payloads map to optional properties in the
underlying Pydantic schemas.

### Common response codes

* `200 OK` – successful reads and updates.
* `201 Created` – successful `POST` to create a resource (tickets, hardware).
* `204 No Content` – not used; deletes return a JSON status payload.
* `401 Unauthorized` – missing/invalid `X‑API‑Key` or unauthenticated session.
* `404 Not Found` – resource does not exist or verification failed.
* `409 Conflict` – attempting to create a client that already exists.
* `422 Unprocessable Entity` – validation failed (missing required fields,
  invalid enum value, etc.).

### Mobile integration data models

The mobile API uses JSON payloads. When building a Swift client, set
`Content-Type: application/json` for request bodies (except file uploads) and
include the `X-API-Key` header with the same token configured on the server.
Timestamps are ISO 8601 strings. Monetary values are returned as strings so the
backend can preserve the formatting that the web UI expects.

#### Ticket payloads

**Create request (`POST /api/v1/tickets`)** – body validated by
`EntryCreate`/`EntryBase`.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `client` | `String?` | No | Human readable client name; the API will fall back to the value stored for the `client_key` if omitted. |
| `client_key` | `String` | Yes | Lookup key from the client table JSON. |
| `start_iso` | `String` | Yes | Start timestamp, ISO 8601 string. |
| `end_iso` | `String?` | No | End timestamp; omit or set `null` while a ticket is active. |
| `note` | `String?` | No | Markdown/plain text body for the entry. |
| `entry_type` | `String` | No | Defaults to `"time"`. Allowed values: `time`, `hardware`, `deployment_flat_rate`. |
| `hardware_id` | `Int?` | No | Numeric hardware FK when logging a hardware sale (required with `entry_type = hardware`). |
| `hardware_barcode` | `String?` | No | Snapshot of the barcode; send if you want the record to reflect the barcode even if the hardware ID changes. |
| `hardware_quantity` | `Int?` | No | Quantity sold/used; must be ≥ 1. |
| `hardware_description` | `String?` | No | Snapshot description for hardware entries. |
| `hardware_sales_price` | `String?` | No | Currency string per unit for hardware entries. |
| `flat_rate_amount` | `String?` | No | Currency string when `entry_type = deployment_flat_rate`. |
| `flat_rate_quantity` | `Int?` | No | Multiplier for flat rate entries; must be ≥ 1 when provided. |
| `invoice_number` | `String?` | No | Optional invoice reference. |
| `sent` | `Int?` | No | Defaults to `0`. Use `1` to mark an entry as invoiced/emailed. |
| `invoiced_total` | `String?` | No | Optional override for the billed total. |

**Update request (`PATCH /api/v1/tickets/{id}`)** – body validated by
`EntryUpdate`. All fields above become optional and may be omitted when not
changing.

**Ticket response (`EntryOut`)** – returned by read, create, update calls.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | `Int` | Primary key. |
| `client` / `client_key` | `String` | Display name and lookup key. |
| `start_iso` / `end_iso` | `String` / `String?` | Raw timestamps stored in the database. |
| `elapsed_minutes` | `Int` | Actual minutes between `start_iso` and `end_iso`. |
| `rounded_minutes` / `rounded_hours` | `Int` / `String` | Rounded values based on the client’s billing increment. |
| `note`, `completed`, `sent`, `invoice_number`, `invoiced_total` | Various | Mirror the stored attributes. |
| `created_at` | `String` | ISO 8601 creation timestamp. |
| `minutes` | `Int` | Persisted working minutes for the entry. |
| `entry_type` | `String` | Echoes the entry classification. |
| `hardware_id`, `hardware_barcode`, `hardware_description`, `hardware_sales_price`, `hardware_quantity` | Optional fields | Present for hardware sales. |
| `flat_rate_amount`, `flat_rate_quantity` | Optional fields | Present for deployment flat-rate tickets. |
| `calculated_value` | `String?` | Server-calculated billing amount (rounded and formatted). |
| `attachments` | `[TicketAttachment]` | Ordered list of attachment metadata (see below). |

**Ticket attachment object** (`GET /api/v1/tickets/{id}/attachments`).

| Field | Type | Notes |
| --- | --- | --- |
| `id` | `String` | Attachment identifier; use in download/delete calls. |
| `filename` | `String` | Original filename. |
| `content_type` | `String?` | MIME type (only image types are accepted on upload). |
| `size` | `Int?` | Size in bytes when recorded. |
| `uploaded_at` | `String` | ISO 8601 timestamp. |
| `url` | `String?` | Direct download path for the resource. |

Upload new attachments by sending `multipart/form-data` with a single `file`
part to `POST /api/v1/tickets/{id}/attachments`. Only PNG, JPEG, GIF and WEBP
images are accepted.

#### Hardware payloads

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `barcode` | `String` | Yes | Normalized and deduplicated when created. |
| `description` | `String` | Yes | Human-readable name for the item. |
| `acquisition_cost` | `String?` | No | Monetary string; may also be provided through header aliases like `X-Acquisition-Cost`. |
| `sales_price` | `String?` | No | Monetary string; header aliases (`X-Sales-Price`, etc.) are accepted. |

Hardware responses (`HardwareOut`) add:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | `Int` | Primary key. |
| `created_at` | `String` | Creation timestamp (`YYYY-MM-DDTHH:MM:SSZ`). |
| `common_vendors` | `[String]` | Vendors recorded on inventory receipts. |
| `average_unit_cost` | `Double?` | Average cost computed from vendor receipts when available. |

#### Inventory payloads

Inventory adjustments (`POST /api/v1/inventory/receive` and `/use`) accept the
following body (`InventoryAdjustment`):

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `hardware_id` | `Int?` | One of `hardware_id` or `barcode` is required. |
| `barcode` | `String?` | Alternate lookup when the numeric ID is unknown. |
| `quantity` | `Int` | Required positive value; the `/use` route automatically applies a negative change. |
| `note` | `String?` | Free-form description of the adjustment. |
| `vendor_name` | `String?` | Populates the vendor counterparty on receipts. |
| `client_name` | `String?` | Populates the client counterparty on usage records. |
| `actual_cost` | `Double?` | Per-unit cost paid to the vendor. |
| `sale_price` | `Double?` | Total sale price billed to the client. |

Inventory events (`InventoryEventOut`) include:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | `Int` | Event identifier. |
| `hardware_id` | `Int` | Foreign key to hardware. |
| `change` | `Int` | Positive for receipts, negative for usage. |
| `source` | `String` | Origin tag (e.g. `api:receive`, `api:use`, `ticket:auto`). |
| `note` | `String?` | Optional description. |
| `created_at` | `String` | ISO 8601 timestamp. |
| `ticket_id` | `Int?` | Linked ticket when auto-generated. |
| `hardware_barcode` / `hardware_description` | `String?` | Snapshots of the hardware metadata. |
| `counterparty_name` / `counterparty_type` | `String?` | Vendor/client context when recorded. |
| `actual_cost` / `unit_cost` | `Double?` | Cost metadata derived from receipts. |
| `sale_price_total` / `sale_unit_price` | `Double?` | Sale totals and per-unit price when provided. |
| `profit_total` / `profit_unit` | `Double?` | Computed profit metrics (`sale_price_total - actual_cost`). |

Inventory summary rows (`GET /api/v1/inventory/summary`) expose:

| Field | Type | Notes |
| --- | --- | --- |
| `hardware_id` | `Int` | Hardware primary key. |
| `barcode` | `String` | Normalized barcode. |
| `description` | `String` | Hardware description. |
| `quantity` | `Int` | On-hand quantity computed from events. |
| `last_activity` | `String?` | ISO timestamp of the most recent event. |

#### Client payloads

The client directory is stored on disk in `client_table.json`. Read-only routes
(`/api/v1/clients`, `/api/v1/clients/{client_key}`, `/api/v1/clients/lookup`)
return:

```
{
  "client_key": "acme",
  "client": {
    "name": "Acme Corp",
    "display_name": "Acme",
    "support_rate": "135",
    "contract": true,
    "<custom attribute keys>": "..."
  }
}
```

Custom attribute keys are listed under the top-level `attribute_keys` array and
can be managed via `POST /api/v1/clients/attributes` and
`DELETE /api/v1/clients/attributes/{key}`. Writes require a valid UI session or
API token.

### Hardware inventory API – `/api/v1/hardware`

| Method & path | Description | Auth required | Notes |
|---------------|-------------|---------------|-------|
| `GET /api/v1/hardware` | List hardware items (newest first). | Yes | Supports `limit` (default `100`) and `offset` query parameters for pagination. |【F:app/routers/api_hardware.py†L12-L15】
| `GET /api/v1/hardware/{item_id}` | Retrieve a single item by numeric id. | Yes | Returns `404` when the id is not found. |【F:app/routers/api_hardware.py†L18-L27】
| `POST /api/v1/hardware` | Create a new hardware record. | Yes | JSON body must include `barcode` and `description`; `acquisition_cost` and `sales_price` are optional. Either field can also be provided via header aliases (see below). |【F:app/routers/api_hardware.py†L30-L45】【F:app/schemas/hardware.py†L6-L24】
| `PATCH /api/v1/hardware/{item_id}` | Update an existing record. | Yes | Any subset of fields may be supplied. `acquisition_cost` and `sales_price` headers override body values. |【F:app/routers/api_hardware.py†L48-L65】
| `DELETE /api/v1/hardware/{item_id}` | Remove a hardware record. | Yes | Responds with `{ "status": "deleted" }` when successful. |【F:app/routers/api_hardware.py†L68-L75】

**Header shortcuts for price fields:** during `POST` and `PATCH`, the service
accepts `Acquisition`/`Sales` values via any of the following header names:
`acquisition-cost`, `acquisition_cost`, `x-acquisition-cost`,
`x_acquisition_cost`, `sales-price`, `sales_price`, `x-sales-price`, and
`x_sales_price`.  Header values take precedence when present.【F:app/routers/api_hardware.py†L33-L45】【F:app/routers/api_hardware.py†L52-L63】

**Example – list hardware**

```http
GET /api/v1/hardware?limit=2&offset=0 HTTP/1.1
Host: tracker.example.com
X-API-Key: your-token
Accept: application/json
```

```json
[
  {
    "id": 42,
    "barcode": "ROUTER-001",
    "description": "4-port router",
    "acquisition_cost": "29.99",
    "sales_price": "49.99",
    "created_at": "2023-09-01T15:24:00Z"
  },
  {
    "id": 41,
    "barcode": "AP-100",
    "description": "Wireless access point",
    "acquisition_cost": null,
    "sales_price": null,
    "created_at": "2023-08-15T19:02:18Z"
  }
]
```

**Example – create hardware**

```http
POST /api/v1/hardware HTTP/1.1
Host: tracker.example.com
X-API-Key: your-token
Content-Type: application/json
x-acquisition-cost: 29.99

{
  "barcode": "ROUTER-002",
  "description": "Rack-mount router"
}
```

```json
{
  "id": 43,
  "barcode": "ROUTER-002",
  "description": "Rack-mount router",
  "acquisition_cost": "29.99",
  "sales_price": null,
  "created_at": "2023-09-05T10:12:45Z"
}
```

### Inventory tracking API – `/api/v1/inventory`

Inventory movements are expressed as signed events linked to hardware rows. The
API exposes the same projections used by the UI: a running summary, the raw
event log, and helpers for receiving or consuming stock. All endpoints require
an API key or logged-in session.【F:app/routers/api_inventory.py†L17-L64】

| Method & path | Description | Auth required | Notes |
|---------------|-------------|---------------|-------|
| `GET /api/v1/inventory/summary` | Return aggregated on-hand counts per hardware item. | Yes | Mirrors the dashboard table; `quantity` is the net sum of all events. |【F:app/routers/api_inventory.py†L33-L35】【F:app/crud/inventory.py†L22-L45】|
| `GET /api/v1/inventory/events` | List inventory events (newest first). | Yes | Supports `limit`/`offset` pagination, defaulting to 100 rows. |【F:app/routers/api_inventory.py†L38-L40】【F:app/crud/inventory.py†L12-L19】|
| `POST /api/v1/inventory/receive` | Record stock received for a hardware item. | Yes | Request body must include a positive `quantity` and either `hardware_id` or `barcode`. |【F:app/routers/api_inventory.py†L43-L52】【F:app/schemas/inventory.py†L8-L18】|
| `POST /api/v1/inventory/use` | Record stock consumption/usage. | Yes | Same payload as `/receive`; the service automatically stores the change as a negative quantity. |【F:app/routers/api_inventory.py†L55-L63】【F:app/schemas/inventory.py†L8-L18】|

Hardware lookups accept either an internal id or a barcode and return `404`
when no match is found. Responses include the linked hardware description and
barcode when available, making it easy to build audit trails.【F:app/routers/api_inventory.py†L20-L40】【F:app/schemas/inventory.py†L21-L33】

**Example – receive stock via barcode**

```http
POST /api/v1/inventory/receive HTTP/1.1
Host: tracker.example.com
X-API-Key: your-token
Content-Type: application/json

{
  "barcode": "ROUTER-002",
  "quantity": 5,
  "note": "Initial stocking order"
}
```

```json
{
  "id": 12,
  "hardware_id": 43,
  "change": 5,
  "source": "api:receive",
  "note": "Initial stocking order",
  "created_at": "2023-09-05T19:45:11Z",
  "ticket_id": null,
  "hardware_barcode": "ROUTER-002",
  "hardware_description": "Rack-mount router"
}
```

### Ticket entries API – `/api/v1/tickets`

Ticket entries can represent billable time (`entry_type="time"`) or a hardware
sale (`entry_type="hardware"`).  Hardware-linked entries automatically copy the
current hardware description and sales price when an item is referenced by id or
barcode.【F:app/crud/tickets.py†L46-L85】  When a ticket is saved in hardware mode,
the system also creates (or updates) a corresponding inventory usage event so
stock levels track every install; reverting to a time entry deletes the event if
it exists.【F:app/crud/tickets.py†L105-L134】【F:app/crud/inventory.py†L89-L121】  Each
record also tracks invoice status with a `sent` flag and optional
`invoice_number`, making it easy to reconcile what's already been
billed.【F:app/schemas/ticket.py†L15-L55】【F:app/crud/tickets.py†L90-L130】

| Method & path | Description | Auth required | Notes |
|---------------|-------------|---------------|-------|
| `GET /api/v1/tickets/active` | List open time entries (no `end_iso`). | Yes | Optional `client_key` filter narrows results to a single client; hardware items are excluded even when unfinished. |【F:app/routers/api_tickets.py†L11-L14】【F:app/crud/tickets.py†L19-L26】
| `GET /api/v1/tickets` | List recent tickets (newest first). | Yes | Returns up to 100 entries (internal default); no pagination parameters are exposed. |【F:app/routers/api_tickets.py†L17-L18】【F:app/crud/tickets.py†L5-L12】
| `GET /api/v1/tickets/{entry_id}` | Retrieve one ticket. | Yes | `404` when the id is missing. |【F:app/routers/api_tickets.py†L21-L29】
| `POST /api/v1/tickets` | Create a ticket entry. | Yes | Body must include `client_key` and `start_iso`. Optional fields include `end_iso`, `note`, `invoice_number`, `sent`, `entry_type`, `hardware_id`, and `hardware_barcode`. |【F:app/routers/api_tickets.py†L32-L41】【F:app/schemas/ticket.py†L6-L35】【F:app/crud/tickets.py†L58-L109】
| `PATCH /api/v1/tickets/{entry_id}` | Update fields on an existing ticket. | Yes | Any subset of fields may be supplied. Updating `client_key` or `client` revalidates the client table; changing `start_iso`/`end_iso` recomputes rounded minutes; switching to `entry_type="hardware"` will relink the referenced hardware. Fields like `sent` and `invoice_number` can be adjusted to reflect billing progress. |【F:app/routers/api_tickets.py†L44-L55】【F:app/crud/tickets.py†L77-L130】
| `GET /api/v1/tickets/{entry_id}/attachments` | List image attachments for a ticket. | Yes | Returns metadata (filename, size, uploaded timestamp) and signed download URLs for each stored file. |【F:app/routers/api_tickets.py†L97-L109】【F:app/crud/tickets.py†L211-L230】
| `POST /api/v1/tickets/{entry_id}/attachments` | Upload a new attachment. | Yes | Accepts `multipart/form-data` with a single image (`png`, `jpg`, `gif`, `webp`). Saved files are written under `/data/attachments/{ticket_id}`. |【F:app/routers/api_tickets.py†L110-L136】【F:app/crud/tickets.py†L212-L228】
| `GET /api/v1/tickets/{entry_id}/attachments/{attachment_id}` | Download an attachment. | Yes | Streams the stored file back with the recorded filename and content type. Returns `404` when the ticket or attachment id is unknown. |【F:app/routers/api_tickets.py†L138-L141】
| `DELETE /api/v1/tickets/{entry_id}` | Remove a ticket entry. | Yes | Returns `{ "status": "deleted" }` when successful. |【F:app/routers/api_tickets.py†L58-L65】

**Example – list active tickets for a client**

```http
GET /api/v1/tickets/active?client_key=acme-co HTTP/1.1
Host: tracker.example.com
X-API-Key: your-token
Accept: application/json
```

```json
[
  {
    "id": 75,
    "client": "Acme Co",
    "client_key": "acme-co",
    "start_iso": "2023-09-05T13:00:00-05:00",
    "end_iso": null,
    "elapsed_minutes": 0,
    "rounded_minutes": 0,
    "rounded_hours": "0.00",
    "note": "Investigating outage",
    "completed": 0,
    "sent": 0,
    "invoice_number": null,
    "created_at": "2023-09-05T18:05:29Z",
    "minutes": 0,
    "entry_type": "time",
    "hardware_id": null,
    "hardware_barcode": null,
    "hardware_description": null,
    "hardware_sales_price": null
  }
]
```

**Example – create a hardware ticket**

```http
POST /api/v1/tickets HTTP/1.1
Host: tracker.example.com
X-API-Key: your-token
Content-Type: application/json

{
  "client_key": "acme-co",
  "entry_type": "hardware",
  "start_iso": "2023-09-05T09:00:00-05:00",
  "end_iso": "2023-09-05T09:15:00-05:00",
  "note": "Sold replacement router",
  "hardware_barcode": "ROUTER-002"
}
```

```json
{
  "id": 76,
  "client": "Acme Co",
  "client_key": "acme-co",
  "start_iso": "2023-09-05T09:00:00-05:00",
  "end_iso": "2023-09-05T09:15:00-05:00",
  "elapsed_minutes": 15,
  "rounded_minutes": 15,
  "rounded_hours": "0.25",
  "note": "Sold replacement router",
  "completed": 0,
  "invoice_number": null,
  "created_at": "2023-09-05T18:10:02Z",
  "minutes": 15,
  "entry_type": "hardware",
  "hardware_id": 43,
  "hardware_barcode": "ROUTER-002",
  "hardware_description": "Rack-mount router",
  "hardware_sales_price": "79.00"
}
```

### Client table API – `/api/v1/clients`

Client metadata is persisted in `client_table.json`.  Read operations are
public; write operations require an API key or logged-in UI session.【F:app/routers/clients.py†L14-L68】

| Method & path | Description | Auth required | Notes |
|---------------|-------------|---------------|-------|
| `GET /api/v1/clients` | Return the entire client table keyed by `client_key`. | No | Response shape: `{ "clients": { … }, "attribute_keys": [ … ] }`. |【F:app/routers/clients.py†L20-L30】
| `GET /api/v1/clients/attributes` | List custom attribute keys tracked alongside clients. | No | Keys are read from (or initialised into) `custom_attributes.json`. |【F:app/routers/clients.py†L28-L30】【F:app/services/custom_attributes.py†L24-L63】
| `GET /api/v1/clients/lookup?name=…` | Resolve a client by display name or key. | No | Responds with `{ "client_key": "…", "client": { … } }` or `404` if unknown. |【F:app/routers/clients.py†L32-L40】
| `GET /api/v1/clients/{client_key}` | Fetch a single client by key. | No | Same payload as lookup. |【F:app/routers/clients.py†L42-L47】
| `POST /api/v1/clients` | Create a client entry. | Yes | Body must include non-empty `client_key` and `name`. Optional `attributes` dict merges into the stored record. |【F:app/routers/clients.py†L50-L68】
| `PATCH /api/v1/clients/{client_key}` | Update a client entry. | Yes | Accepts optional `name` and `attributes` keys. Blank names are rejected. |【F:app/routers/clients.py†L70-L89】
| `POST /api/v1/clients/attributes` | Append a custom attribute key. | Yes | Validates that the key is non-empty and not reserved; returns the sorted list of keys. |【F:app/routers/clients.py†L102-L113】【F:app/services/custom_attributes.py†L65-L105】
| `DELETE /api/v1/clients/attributes/{attribute_key}` | Remove a custom attribute key (and strip it from stored clients). | Yes | Rejects blank or unknown keys, then cascades removal across all clients. |【F:app/routers/clients.py†L116-L140】【F:app/services/custom_attributes.py†L87-L111】
| `POST /api/v1/clients/{client_key}/delete` | Delete via POST (UI compatibility). | Yes | Equivalent to the `DELETE` endpoint. |【F:app/routers/clients.py†L91-L102】
| `DELETE /api/v1/clients/{client_key}` | Delete via RESTful verb. | Yes | Returns `{ "status": "deleted", "client_key": "…" }`. |【F:app/routers/clients.py†L91-L102】|

**Example – list clients**

```http
GET /api/v1/clients HTTP/1.1
Host: tracker.example.com
Accept: application/json
```

```json
{
  "clients": {
    "acme-co": {
      "name": "Acme Co",
      "contact": "support@acme.example",
      "billing_rate": "125"
    },
    "globex": {
      "name": "Globex Corporation",
      "billing_rate": "140"
    }
  },
  "attribute_keys": [
    "billing_rate",
    "contact"
  ]
}
```

The companion `attribute_keys` array mirrors the registry stored on disk so
headless clients can render custom fields alongside built-in demographics.【F:app/routers/clients.py†L20-L30】【F:app/services/custom_attributes.py†L24-L83】

**Example – update a client**

```http
PATCH /api/v1/clients/acme-co HTTP/1.1
Host: tracker.example.com
X-API-Key: your-token
Content-Type: application/json

{
  "name": "Acme Co",
  "attributes": {
    "contact": "it@acme.example",
    "notes": "Switch maintenance to quarterly"
  }
}
```

```json
{
  "status": "updated",
  "client_key": "acme-co",
  "client": {
    "name": "Acme Co",
    "contact": "it@acme.example",
    "billing_rate": "125",
    "notes": "Switch maintenance to quarterly"
  }
}
```

### Address autocomplete & verification API – `/api/v1/address`

These endpoints call Google Places Autocomplete and the Address Validation API
using the shared Maps API key and are guarded by the same API token/session
requirement as other headless routes.【F:app/routers/address.py†L5-L51】 When the
Google credentials are missing, `/suggest` returns an empty `suggestions`
array and `/verify` responds with `{ "candidate": null }` instead of an error
so the UI can fall back to manual entry.【F:app/routers/address.py†L32-L50】【F:app/services/address.py†L15-L231】

| Method & path | Description | Query parameters | Notes |
|---------------|-------------|------------------|-------|
| `GET /api/v1/address/suggest` | Autocomplete address text. | `query` (required search string, alias `q`), optional `city`, `state`, `zip` (alias `postal_code`), `limit` (1–20, default 8). | Returns `{ "suggestions": [ … ] }` enriched with Google Place details and coordinates. |【F:app/routers/address.py†L19-L33】
| `GET /api/v1/address/verify` | Verify a selected address. | Required `street` (alias `street_line`); optional `city`, `state`, `zip` (alias `postal_code`), `secondary`, `place_id`. | Returns `{ "candidate": { … } }` on success, `404` if the address cannot be verified. |【F:app/routers/address.py†L36-L51】

**Example – autocomplete request**

```http
GET /api/v1/address/suggest?query=1600+Amphitheatre&city=Mountain+View&state=CA HTTP/1.1
Host: tracker.example.com
X-API-Key: your-token
Accept: application/json
```

```json
{
  "suggestions": [
    {
      "street_line": "1600 Amphitheatre Pkwy",
      "secondary": "",
      "city": "Mountain View",
      "state": "CA",
      "postal_code": "94043",
      "country": "US",
      "formatted": "1600 Amphitheatre Pkwy, Mountain View, CA 94043, USA",
      "place_id": "ChIJ2eUgeAK6j4ARbn5u_wAGqWA",
      "result_type": "street_address",
      "confidence": null,
      "lat": 37.4220656,
      "lon": -122.0840897,
      "county": "Santa Clara County"
    }
  ]
}
```

**Example – verify address by place id**

```http
GET /api/v1/address/verify?place_id=ChIJ2eUgeAK6j4ARbn5u_wAGqWA HTTP/1.1
Host: tracker.example.com
X-API-Key: your-token
Accept: application/json
```

```json
{
  "candidate": {
    "delivery_line_1": "1600 Amphitheatre Pkwy",
    "delivery_line_2": "",
    "last_line": "Mountain View, CA 94043",
    "city": "Mountain View",
    "state": "CA",
    "postal_code": "94043",
    "country": "US",
    "county": "Santa Clara County",
    "dpv_match_code": null,
    "footnotes": null,
    "latitude": 37.4220656,
    "longitude": -122.0840897,
    "place_id": "ChIJ2eUgeAK6j4ARbn5u_wAGqWA",
    "confidence": null
  }
}
```

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
| `GOOGLE_MAPS_API_KEY` | Google Maps Platform API key for autocomplete, validation, and map embeds | empty (disabled) |
| `GOOGLE_PLACES_AUTOCOMPLETE_URL` | Override for the Google Places Autocomplete REST endpoint | Google default |
| `GOOGLE_PLACES_DETAILS_URL` | Override for the Google Places Details REST endpoint | Google default |
| `GOOGLE_ADDRESS_VALIDATION_URL` | Override for the Google Address Validation REST endpoint | Google default |
| `GOOGLE_ADDRESS_VALIDATION_REGION_CODE` | Default ISO region code sent to the Address Validation API | `US` |

Refer to `app/core/config.py` and `docker-compose.yml` for the full list of
environment variables and their defaults.

### Address autocomplete setup

Address prefill in the client editor is powered by Google Places Autocomplete
and the Address Validation API. To enable it:

1. **Create or reuse a Google Cloud project** with billing enabled, then turn on
   the **Places API** and **Address Validation API** (the existing Maps
   JavaScript API is also required if you use the embedded maps).
2. **Generate a restricted API key** that is allowed to call the enabled
   services and lock it to the domains/IPs where this app runs.
3. **Set the `GOOGLE_MAPS_API_KEY` environment variable** for the application
   (for example in `.env` or your Docker Compose file). Optionally override
   `GOOGLE_ADDRESS_VALIDATION_REGION_CODE` if most lookups occur outside the
   United States.
4. Restart the application. When editing a client, typing into **Address Line 1**
   displays Google-powered suggestions, and picking one automatically fills the
   remaining city/state/ZIP fields once validated.

If the credentials are omitted, the UI silently falls back to manual entry.

### Google Maps client map setup & maintenance

The client editor modal and the Clients page can embed Google Maps whenever a
mailing address is available. The editor shows a single-location preview for the
client you're editing, while the list view aggregates every mappable client into
pins at the bottom of the page so you can visualise coverage at a glance. To
enable and maintain this integration:

1. **Create or reuse a Google Cloud project** with billing enabled, then
   activate the **Maps JavaScript**, **Geocoding**, **Places**, and **Address
   Validation** APIs. These cover map rendering, coordinate lookups, and the
   autocomplete/verification flows described above.
2. **Generate a restricted API key** scoped to the enabled Google Maps
   Platform services and lock it to your production domains and/or IP
   addresses.
3. **Set the `GOOGLE_MAPS_API_KEY` environment variable** for the application
   (for example in `.env`, `docker-compose.yml`, or your hosting secrets). The
   key is injected into both the client editor and list templates at render
   time.
4. **Restart the application** so the new environment variable is picked up.
   Opening a client with a populated address now shows a pinned map inside the
   modal, and the Clients page automatically renders the overview map once
   clients have mappable addresses. Edits to an address live-update the preview
   and refreshed list data updates the pins.

For long-term maintenance:

* Rotate the API key on a regular cadence and update the corresponding
  environment variable before revoking the old key.
* Monitor usage and quota alerts in the Google Cloud console so unexpected
  traffic does not disable the embed.
* If you need to temporarily disable the map (for example, during maintenance
  or cost controls), unset `GOOGLE_MAPS_API_KEY`; the UI automatically hides the
  modal preview and Clients page overview map while continuing to function with
  manual address entry only.【F:README.md†L720-L752】

## Contributing

This project currently targets a single-user workflow.  Future enhancements
might include multi-user support, more granular permissions, richer client
management and improved reporting.  Pull requests are welcome!  Please
ensure new code is well-tested and keep changes focused on a single purpose.

## License

Include the appropriate license information here if one exists.  Otherwise,
replace this section or remove it as needed.
