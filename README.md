# Place Finder

A Django web app for finding vacation-rental properties by location. It combines:

- **Semantic location search**: type a place name and get autocomplete suggestions ranked by meaning, using `fastembed` (`all-MiniLM-L6-v2`) embeddings stored in **pgvector**.
- **Geo queries**: properties are stored as **PostGIS** points, so the app can find properties near a given listing (`radius_km`).
- **REST API** built with Django REST Framework, plus server-rendered pages for browsing.

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend | Django 6.1, Django REST Framework |
| Database | PostgreSQL 17 + PostGIS 3 + pgvector (Docker) |
| Embeddings | fastembed (ONNX), 384-dim vectors |
| Data | pandas CSV importer |

## Prerequisites

- **Python 3.12+** (with `venv`)
- **Docker** with Docker Compose
- **GDAL, GEOS and PROJ** system libraries (required by `django.contrib.gis`)
  - Ubuntu/Debian: `sudo apt install gdal-bin libgdal-dev libgeos-dev libproj-dev`
  - macOS: `brew install gdal geos proj`
- Internet access on first run (the embedding model is downloaded once)

## Important: the `img/` folder

The `static/img/` folder (property photos such as `house.jpg`, `villa.jpg`, `apartment.jpg`, and `favicon.png`) is **not included in this copy** to keep the download small. It exists in the main repository. Make sure `static/img/` is present before running, otherwise pages still work but images will be broken.

## Quick start (recommended)

```bash
chmod +x run.sh
./run.sh
```

Then open <http://127.0.0.1:8000/>.

`run.sh` does everything in order:

1. Checks Python, Docker and GDAL
2. Creates a virtual environment in `venv/`
3. Installs `requirements.txt`
4. Starts PostgreSQL + PostGIS + pgvector with Docker Compose
5. Waits for the database and verifies the extensions
6. Runs migrations
7. Imports **`world_properties_synthetic.csv`** and embeds all location names
8. Starts the dev server

Running it again is safe: existing venv, dependencies and data are detected and skipped.

### `run.sh` options

| Option | Description |
|--------|-------------|
| `--port 9000` | Run on a different port (default `8000`) |
| `--host 0.0.0.0` | Expose the server on your network |
| `--csv <file>` | Import a different CSV from the project root |
| `--reimport` | Re-import the CSV and update existing rows |
| `--skip-import` | Skip the data import step |
| `--install-system-deps` | Install GDAL/GEOS/PROJ via apt or brew |
| `--stop` | Stop the database container (data kept) |
| `--reset` | Stop the database and **delete** its data volume |

## Manual setup

If you prefer to run each step yourself:

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the database (PostgreSQL + PostGIS + pgvector)
docker compose up -d --build

# 4. Verify extensions (optional)
python scripts/db_connection_test.py

# 5. Apply migrations
python manage.py migrate

# 6. Import the world dataset and generate location embeddings
python manage.py import_properties world_properties_synthetic.csv

# 7. Run the app
python manage.py runserver
```

### Import command options

```bash
python manage.py import_properties world_properties_synthetic.csv            # import world data
python manage.py import_properties world_properties_synthetic.csv --dry-run  # parse only, save nothing
python manage.py import_properties world_properties_synthetic.csv --update   # update existing rows
python manage.py import_properties                                           # default: bangladesh_properties_synthetic.csv
```

Datasets included:

- `world_properties_synthetic.csv`: listings across cities worldwide (used by default in this guide)
- `bangladesh_properties_synthetic.csv`: Bangladesh-only listings

All listings are synthetic sample data, not real properties.

## Database settings

Defined in `docker-compose.yml` and `core/settings.py`:

| Setting | Value |
|---------|-------|
| Host | `localhost` |
| Port | `5442` |
| Database | `appdb` |
| User / Password | `postgres` / `postgres` |

## Endpoints

| URL | Description |
|-----|-------------|
| `/` | Home page with location search |
| `/api/v1/locations/health/` | Health check (JSON) |
| `/api/v1/locations/autocomplete/?search=<text>` | Semantic location suggestions (min. 2 chars) |
| `/api/v1/locations/properties/?location_id=<id>&limit=9&offset=0` | Properties in a location |
| `/api/v1/locations/nearby-properties/?id=<property_id>&radius_km=5&limit=12` | Properties near a listing |
| `/admin/` | Django admin (`python manage.py createsuperuser` first) |

## Project structure

```
.
├── core/                 # Django project (settings, urls, home view)
├── properties/           # Main app (models, API, views, importer, embeddings)
│   └── management/commands/import_properties.py
├── templates/            # HTML templates
├── static/               # css/, js/ (and img/ in the main repo)
├── scripts/              # db_connection_test.py
├── Dockerfile            # Postgres 17 + PostGIS + pgvector
├── docker-compose.yml
├── requirements.txt
├── *.csv                 # Synthetic datasets
├── run.sh                # One-command setup & run
└── manage.py
```

## Troubleshooting

- **`Could not find the GDAL library`**: install GDAL/GEOS/PROJ (see Prerequisites), or run `./run.sh --install-system-deps`.
- **Port 5442 already in use**: stop whatever uses it, or change the host port in `docker-compose.yml` and in `DATABASES` in `core/settings.py`.
- **Database not ready / connection refused**: check `docker logs postgres-postgis-pgvector`.
- **Broken images**: the `static/img/` folder is missing; copy it from the main repo.
- **Start from scratch**: `./run.sh --reset && ./run.sh`.
- **Stop the database**: `./run.sh --stop` (or `docker compose down`).
