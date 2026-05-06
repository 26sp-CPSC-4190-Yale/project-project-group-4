#!/usr/bin/env bash
# One-shot setup for a fresh Ubuntu 22.04 / 24.04 VM.
#
# What this script does:
#   1. apt-installs Python 3.13 build deps, Node 20, PostgreSQL 16, and basic tools.
#   2. Installs `uv` (Python package manager) for the current user.
#   3. Creates a local `yartmatch` PostgreSQL database and `yart` role.
#   4. Restores data/yartmatch.sql.gz into that database (if present).
#   5. Writes a working .env if one does not already exist.
#   6. Installs backend Python deps via `uv sync`.
#   7. Runs Django migrations and createcachetable.
#   8. Installs frontend npm deps and writes frontend/.env.
#
# What this script does NOT do:
#   - Start the dev servers (run them yourself, see SETUP.md).
#   - Create a Django superuser (optional, see SETUP.md).
#
# Re-running is safe; each step checks before mutating state.

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

DB_NAME="${DB_NAME:-yartmatch}"
DB_USER="${DB_USER:-yart}"
DB_PASSWORD="${DB_PASSWORD:-yart}"
DUMP_GZ="$ROOT/data/yartmatch.sql.gz"
DUMP_SQL="$ROOT/data/yartmatch.sql"

log()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!! %s\033[0m\n' "$*"; }

require_ubuntu() {
  if ! command -v apt-get >/dev/null 2>&1; then
    warn "This script targets Ubuntu/Debian. apt-get not found. See SETUP.md for manual steps."
    exit 1
  fi
}

apt_install() {
  log "Installing system packages"
  sudo apt-get update -y
  sudo apt-get install -y \
    build-essential curl ca-certificates git lsb-release gnupg \
    python3 python3-venv python3-dev \
    libpq-dev

  # PostgreSQL 17 from the official PGDG apt repo — needed because Ubuntu
  # 24.04 still ships pg 16 by default, and the production dump is pg 17.
  if ! dpkg -l postgresql-17 >/dev/null 2>&1; then
    log "Adding PGDG apt repo and installing PostgreSQL 17"
    sudo install -d /usr/share/postgresql-common/pgdg
    sudo curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
      https://www.postgresql.org/media/keys/ACCC4CF8.asc
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
      | sudo tee /etc/apt/sources.list.d/pgdg.list >/dev/null
    sudo apt-get update -y
    sudo apt-get install -y postgresql-17 postgresql-contrib-17
  fi

  if ! command -v node >/dev/null 2>&1 || [[ "$(node -v 2>/dev/null)" != v20* && "$(node -v 2>/dev/null)" != v22* ]]; then
    log "Installing Node.js 20.x"
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
  fi
}

install_uv() {
  if command -v uv >/dev/null 2>&1; then
    return
  fi
  log "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  if ! command -v uv >/dev/null 2>&1; then
    warn "uv installed but not on PATH. Add ~/.local/bin to PATH and rerun."
    exit 1
  fi
}

setup_postgres() {
  log "Configuring PostgreSQL"
  sudo systemctl enable --now postgresql

  if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
    sudo -u postgres psql -c "CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASSWORD' CREATEDB;"
  fi

  if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
  fi
}

restore_dump() {
  # Accept either yartmatch.sql.gz (gzipped) or yartmatch.sql (plain) —
  # Google Drive auto-decompresses .gz on download, so the file may arrive
  # in either form depending on how it was distributed.
  if [ -f "$DUMP_GZ" ]; then
    log "Restoring $DUMP_GZ into $DB_NAME"
    PGPASSWORD="$DB_PASSWORD" gunzip -c "$DUMP_GZ" | \
      psql -v ON_ERROR_STOP=0 -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" >/dev/null
  elif [ -f "$DUMP_SQL" ]; then
    log "Restoring $DUMP_SQL into $DB_NAME"
    PGPASSWORD="$DB_PASSWORD" psql -v ON_ERROR_STOP=0 \
      -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" -f "$DUMP_SQL" >/dev/null
  else
    warn "No dump file at $DUMP_GZ or $DUMP_SQL — skipping restore."
    warn "The app will start but the artwork catalog will be empty. See SETUP.md."
  fi
}

write_env() {
  if [ -f .env ]; then
    log ".env already exists — leaving it alone"
    return
  fi
  log "Writing .env"
  SECRET=$("$ROOT/.venv/bin/python" -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" 2>/dev/null \
    || python3 -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits+'!@#$%^&*(-_=+)') for _ in range(50)))")
  cat > .env <<EOF
SECRET_KEY=$SECRET
DEBUG=True
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@127.0.0.1:5432/$DB_NAME
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
EOF
}

backend_deps() {
  log "Installing backend dependencies (uv sync)"
  uv sync
}

run_migrations() {
  log "Running Django migrations"
  uv run python manage.py migrate --noinput
  log "Creating Django cache table (idempotent)"
  uv run python manage.py createcachetable || true
}

frontend_deps() {
  log "Installing frontend dependencies"
  ( cd frontend && npm install )
  if [ ! -f frontend/.env ]; then
    log "Writing frontend/.env"
    echo "VITE_API_URL=http://127.0.0.1:8000" > frontend/.env
  fi
}

main() {
  require_ubuntu
  apt_install
  install_uv
  setup_postgres
  restore_dump
  backend_deps
  write_env       # needs .venv to exist for django's get_random_secret_key
  run_migrations
  frontend_deps

  cat <<EOF

================================================================
Setup complete.

Start the backend (terminal 1):
  uv run python manage.py runserver 127.0.0.1:8000

Start the frontend (terminal 2):
  cd frontend && npm run dev -- --host 127.0.0.1

Then open http://localhost:5173 in a browser.

To create an admin user (optional):
  uv run python manage.py createsuperuser
================================================================
EOF
}

main "$@"
