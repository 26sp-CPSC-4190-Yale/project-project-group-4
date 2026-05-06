#!/usr/bin/env bash
# Sets up YArt Match on a fresh Ubuntu 22.04 / 24.04 VM. Safe to rerun.
set -euo pipefail

cd "$(dirname "$0")/.."

DB_NAME="${DB_NAME:-yartmatch}"
DB_USER="${DB_USER:-yart}"
DB_PASSWORD="${DB_PASSWORD:-yart}"

if ! command -v apt-get >/dev/null; then
    echo "This script targets Ubuntu/Debian. See SETUP.md for other systems." >&2
    exit 1
fi

echo ">> apt packages"
sudo apt-get update -y
sudo apt-get install -y \
    build-essential curl ca-certificates git lsb-release gnupg \
    python3 python3-venv python3-dev libpq-dev

# Postgres 17. Ubuntu 24.04 still ships pg 16, but the Neon dump is 17.
if ! dpkg -l postgresql-17 >/dev/null 2>&1; then
    echo ">> Postgres 17 (PGDG)"
    sudo install -d /usr/share/postgresql-common/pgdg
    sudo curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
        https://www.postgresql.org/media/keys/ACCC4CF8.asc
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
        | sudo tee /etc/apt/sources.list.d/pgdg.list >/dev/null
    sudo apt-get update -y
    sudo apt-get install -y postgresql-17 postgresql-contrib-17
fi

case "$(node -v 2>/dev/null || echo none)" in
    v20*|v22*) ;;
    *)
        echo ">> Node 20"
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y nodejs
        ;;
esac

if ! command -v uv >/dev/null; then
    echo ">> uv"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    if [ -f "$HOME/.bashrc" ] && ! grep -q '/.local/bin' "$HOME/.bashrc"; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    fi
fi

echo ">> postgres role + database"
sudo systemctl enable --now postgresql
sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 \
    || sudo -u postgres psql -c "CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASSWORD' CREATEDB;"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 \
    || sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

echo ">> restoring dump"
if [ -f data/yartmatch.sql.gz ]; then
    PGPASSWORD="$DB_PASSWORD" gunzip -c data/yartmatch.sql.gz \
        | psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" >/dev/null
elif [ -f data/yartmatch.sql ]; then
    PGPASSWORD="$DB_PASSWORD" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" \
        -f data/yartmatch.sql >/dev/null
else
    echo "   no dump in data/, skipping (catalog will be empty)"
fi

echo ">> backend deps"
uv sync

if [ ! -f .env ]; then
    echo ">> writing .env"
    SECRET=$(uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
    cat > .env <<EOF
SECRET_KEY=$SECRET
DEBUG=True
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@127.0.0.1:5432/$DB_NAME
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
EOF
fi

echo ">> migrations"
uv run python manage.py migrate --noinput
uv run python manage.py createcachetable || true

echo ">> frontend deps"
( cd frontend && npm install )
[ -f frontend/.env ] || echo "VITE_API_URL=http://127.0.0.1:8000" > frontend/.env

cat <<'EOF'

Done. Open two shells:

  uv run python manage.py runserver 127.0.0.1:8000
  cd frontend && npm run dev -- --host 127.0.0.1

Then http://localhost:5173.
EOF
