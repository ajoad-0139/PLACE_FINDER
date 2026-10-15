#!/usr/bin/env bash
# =============================================================================
# Place Finder - one-command setup & run script
#
#   1. checks prerequisites (python3, docker, GDAL/GEOS)
#   2. creates a Python virtual environment (venv/)
#   3. installs dependencies from requirements.txt
#   4. starts PostgreSQL + PostGIS + pgvector with Docker
#   5. runs Django migrations
#   6. imports the world dataset (world_properties_synthetic.csv) + embeddings
#   7. starts the Django development server
#
# Usage:
#   ./run.sh                      # full setup + run on 127.0.0.1:8000
#   ./run.sh --port 9000          # use another port
#   ./run.sh --host 0.0.0.0       # expose on the network
#   ./run.sh --csv bangladesh_properties_synthetic.csv   # import another CSV
#   ./run.sh --reimport           # re-import CSV and update existing rows
#   ./run.sh --skip-import        # do not import data
#   ./run.sh --install-system-deps  # try to install GDAL/GEOS/PROJ (apt/brew)
#   ./run.sh --stop               # stop the database container
#   ./run.sh --reset              # stop DB and DELETE its data volume
#   ./run.sh -h | --help
# =============================================================================
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

# ----------------------------- configuration ---------------------------------
PROJECT_NAME="Place Finder"
VENV_DIR="venv"
HOST="127.0.0.1"
PORT="8000"
CSV_FILE="world_properties_synthetic.csv"
DB_SERVICE="postgres"
DB_CONTAINER="postgres-postgis-pgvector"
DB_USER="postgres"
DB_NAME="appdb"
DB_PORT="5442"
SKIP_IMPORT=0
REIMPORT=0
INSTALL_SYSTEM_DEPS=0
ACTION="run"

# ------------------------------- helpers -------------------------------------
if [ -t 1 ]; then
  BLUE=$'\033[1;34m'; GREEN=$'\033[1;32m'; YELLOW=$'\033[1;33m'; RED=$'\033[1;31m'; NC=$'\033[0m'
else
  BLUE=""; GREEN=""; YELLOW=""; RED=""; NC=""
fi
step() { echo "${BLUE}==>${NC} $*"; }
ok()   { echo "${GREEN} ok${NC} $*"; }
warn() { echo "${YELLOW}warn${NC} $*"; }
die()  { echo "${RED}error${NC} $*" >&2; exit 1; }

usage() { sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0; }

# ----------------------------- argument parsing ------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --host)                HOST="${2:?--host needs a value}"; shift 2 ;;
    --port)                PORT="${2:?--port needs a value}"; shift 2 ;;
    --csv)                 CSV_FILE="${2:?--csv needs a value}"; shift 2 ;;
    --skip-import)         SKIP_IMPORT=1; shift ;;
    --reimport)            REIMPORT=1; shift ;;
    --install-system-deps) INSTALL_SYSTEM_DEPS=1; shift ;;
    --stop)                ACTION="stop"; shift ;;
    --reset)               ACTION="reset"; shift ;;
    -h|--help)             usage ;;
    *) die "Unknown option: $1 (try --help)" ;;
  esac
done

# ------------------------------ docker compose -------------------------------
command -v docker >/dev/null 2>&1 || die "Docker is not installed. Install it from https://docs.docker.com/get-docker/"
docker info >/dev/null 2>&1 || die "Docker is installed but the daemon is not running (or you lack permission). Start Docker and retry."

if docker compose version >/dev/null 2>&1; then
  DC=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  DC=(docker-compose)
else
  die "Docker Compose not found. Install the Docker Compose plugin."
fi

if [ "$ACTION" = "stop" ]; then
  step "Stopping database container"
  "${DC[@]}" down
  ok "Stopped (data volume kept)."
  exit 0
fi

if [ "$ACTION" = "reset" ]; then
  step "Stopping database and deleting its data volume"
  "${DC[@]}" down -v
  ok "Database wiped. Run ./run.sh to start fresh."
  exit 0
fi

# ------------------------------ system packages ------------------------------
# django.contrib.gis needs the GDAL, GEOS and PROJ libraries on the host.
install_system_deps() {
  step "Installing GDAL / GEOS / PROJ system libraries"
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3-venv python3-dev build-essential \
      gdal-bin libgdal-dev libgeos-dev libproj-dev
  elif command -v brew >/dev/null 2>&1; then
    brew install gdal geos proj
  else
    die "Unsupported package manager. Install GDAL, GEOS and PROJ manually."
  fi
}

gdal_present() {
  if command -v gdal-config >/dev/null 2>&1; then return 0; fi
  if command -v ldconfig >/dev/null 2>&1 && ldconfig -p 2>/dev/null | grep -q libgdal; then return 0; fi
  if command -v brew >/dev/null 2>&1 && brew list gdal >/dev/null 2>&1; then return 0; fi
  return 1
}

if [ "$INSTALL_SYSTEM_DEPS" -eq 1 ]; then
  install_system_deps
elif ! gdal_present; then
  warn "GDAL/GEOS libraries were not detected. Django GIS needs them."
  warn "Run './run.sh --install-system-deps' or install manually:"
  warn "  Ubuntu/Debian: sudo apt install gdal-bin libgdal-dev libgeos-dev libproj-dev"
  warn "  macOS:         brew install gdal geos proj"
fi

# --------------------------------- python ------------------------------------
step "Checking Python"
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  die "Python not found. Install Python 3.12+."
fi

"$PY" - << 'PYEOF' || die "Python 3.12+ is required (Django 6.x)."
import sys
sys.exit(0 if sys.version_info >= (3, 12) else 1)
PYEOF
ok "$($PY --version)"

# ---------------------------------- venv -------------------------------------
if [ ! -d "$VENV_DIR" ]; then
  step "Creating virtual environment in ./$VENV_DIR"
  "$PY" -m venv "$VENV_DIR" || die "Could not create venv. On Ubuntu: sudo apt install python3-venv"
else
  ok "Virtual environment already exists (./$VENV_DIR)"
fi

# shellcheck disable=SC1091
if [ -f "$VENV_DIR/bin/activate" ]; then
  source "$VENV_DIR/bin/activate"
else
  source "$VENV_DIR/Scripts/activate"   # Windows Git Bash
fi

# ------------------------------- dependencies --------------------------------
step "Installing Python dependencies"
python -m pip install --quiet --upgrade pip
# reinstall only when requirements.txt changed since the last successful install
REQ_HASH="$(python - << 'PYEOF'
import hashlib
print(hashlib.sha256(open("requirements.txt", "rb").read()).hexdigest())
PYEOF
)"
STAMP="$VENV_DIR/.requirements.sha256"
if [ -f "$STAMP" ] && [ "$(cat "$STAMP")" = "$REQ_HASH" ]; then
  ok "Dependencies already up to date"
else
  python -m pip install -r requirements.txt
  echo "$REQ_HASH" > "$STAMP"
  ok "Dependencies installed"
fi

# ---------------------------------- docker -----------------------------------
step "Starting PostgreSQL + PostGIS + pgvector (Docker)"
"${DC[@]}" up -d --build "$DB_SERVICE"

step "Waiting for the database to accept connections"
for i in $(seq 1 60); do
  if docker exec "$DB_CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
    ok "Database is ready (localhost:$DB_PORT)"
    break
  fi
  if [ "$i" -eq 60 ]; then
    die "Database did not become ready in time. Check: docker logs $DB_CONTAINER"
  fi
  sleep 2
done
# pg_isready can pass during first-boot init; give Postgres a moment to restart
sleep 2

step "Verifying PostGIS and pgvector extensions"
python scripts/db_connection_test.py

# -------------------------------- migrations ---------------------------------
step "Running migrations"
python manage.py migrate --noinput

# ----------------------------------- data ------------------------------------
if [ "$SKIP_IMPORT" -eq 1 ]; then
  warn "Skipping data import (--skip-import)"
else
  [ -f "$CSV_FILE" ] || die "CSV file not found: $CSV_FILE"
  EXISTING="$(python manage.py shell -c 'from properties.models import Property; print(Property.objects.count())' 2>/dev/null | tail -n 1)"
  if [ "$REIMPORT" -eq 1 ]; then
    step "Re-importing $CSV_FILE (updating existing rows)"
    python manage.py import_properties "$CSV_FILE" --update
  elif [ "${EXISTING:-0}" -gt 0 ] 2>/dev/null; then
    ok "Database already has $EXISTING properties - skipping import (use --reimport to force)"
  else
    step "Importing $CSV_FILE and generating embeddings (first run downloads the embedding model)"
    python manage.py import_properties "$CSV_FILE"
  fi
fi

# --------------------------------- warnings ----------------------------------
if [ ! -d "static/img" ]; then
  warn "static/img/ is missing - property photos and the favicon will not load."
  warn "It lives in the main repository; copy it into ./static/img/"
fi

# ----------------------------------- run -------------------------------------
step "Starting $PROJECT_NAME at http://$HOST:$PORT  (Ctrl+C to stop)"
echo "    Home:    http://$HOST:$PORT/"
echo "    Health:  http://$HOST:$PORT/api/v1/locations/health/"
echo "    Admin:   http://$HOST:$PORT/admin/   (create a user: python manage.py createsuperuser)"
exec python manage.py runserver "$HOST:$PORT"
