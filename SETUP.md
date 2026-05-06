# Running YArt Match on a Linux VM

Setup notes for a fresh Ubuntu 22.04 / 24.04 box. You need a user with
sudo. Nothing else has to be preinstalled.

The hosted version of the app uses Vercel (frontend), Render (backend),
and Neon (Postgres). On the VM everything runs locally instead.

## Database dump

The artwork catalog lives in a Postgres dump that isn't in the repo.
Download it from Google Drive:

> [yartmatch.sql.gz](https://drive.google.com/file/d/17X5OMsquXdnGpmEHFGjKCF26RHFjHR-Q/view?usp=sharing)

Put it in `data/`. Drive auto-decompresses gzipped files on download, so
you might end up with `yartmatch.sql.gz` *or* `yartmatch.sql`. Either is
fine — the script and the manual steps below handle both. Just don't
rename it.

## One-shot setup

```bash
git clone <repo-url> yart
cd yart
mkdir -p data
# drop the dump file in data/
./scripts/setup.sh
```

When it finishes, in two shells:

```bash
uv run python manage.py runserver 127.0.0.1:8000
```

```bash
cd frontend && npm run dev -- --host 127.0.0.1
```

Then http://localhost:5173.

## Manual setup

Same steps without the script. Use this if `setup.sh` errors out or you
want to see exactly what it's doing.

### System packages

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential curl ca-certificates git lsb-release gnupg \
    python3 python3-venv python3-dev libpq-dev

# Postgres 17 (Ubuntu still defaults to 16; the dump is 17):
sudo install -d /usr/share/postgresql-common/pgdg
sudo curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
    https://www.postgresql.org/media/keys/ACCC4CF8.asc
echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
    | sudo tee /etc/apt/sources.list.d/pgdg.list
sudo apt-get update
sudo apt-get install -y postgresql-17 postgresql-contrib-17

# Node 20:
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

If your `python3` is older than 3.13 (Ubuntu 22.04 ships 3.10):

```bash
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.13 python3.13-venv python3.13-dev
```

`uv` will pick up 3.13 from `pyproject.toml`.

### uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"   # add to ~/.bashrc to persist
```

### Postgres role + database

```bash
sudo systemctl enable --now postgresql
sudo -u postgres psql <<SQL
CREATE ROLE yart LOGIN PASSWORD 'yart' CREATEDB;
CREATE DATABASE yartmatch OWNER yart;
SQL

PGPASSWORD=yart psql -h 127.0.0.1 -U yart -d yartmatch -c '\conninfo'
```

### Restore the dump

Pick whichever matches what you downloaded:

```bash
gunzip -c data/yartmatch.sql.gz | PGPASSWORD=yart psql -h 127.0.0.1 -U yart -d yartmatch
# or
PGPASSWORD=yart psql -h 127.0.0.1 -U yart -d yartmatch -f data/yartmatch.sql
```

The dump uses `--clean --if-exists`, so re-running it is safe.

### .env

```bash
cp .env.example .env
```

Then fill it in:

- `SECRET_KEY` — `uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- `DEBUG=True`
- `DATABASE_URL=postgresql://yart:yart@127.0.0.1:5432/yartmatch`
- `ALLOWED_HOSTS=localhost,127.0.0.1`
- `CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`
  (both — browsers treat `localhost` and `127.0.0.1` as different origins)

### Backend

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py createcachetable
```

Optional, for `/admin/`:

```bash
uv run python manage.py createsuperuser
```

### Frontend

```bash
cd frontend
npm install
echo 'VITE_API_URL=http://127.0.0.1:8000' > .env
cd ..
```

### Run

```bash
uv run python manage.py runserver 127.0.0.1:8000
```

```bash
cd frontend && npm run dev -- --host 127.0.0.1
```

http://localhost:5173. Register an account and you're in.

## Tests

```bash
uv run python manage.py test gallery --verbosity=2
```

The first run is slow because it builds the test DB from scratch. Add
`--keepdb` after that.

## Reaching a headless VM

If you're SSH'd into the VM, forward the ports from your laptop:

```bash
ssh -L 5173:localhost:5173 -L 8000:localhost:8000 user@vm
```

Then http://localhost:5173 on the laptop hits the VM. Nothing's exposed
publicly.

If you'd rather bind the dev servers to the external interface: run them
with `--host 0.0.0.0`, add the VM's IP to `ALLOWED_HOSTS`, and point
`VITE_API_URL` at the VM's URL. Don't do this on the public internet —
`DEBUG=True` and neither dev server is hardened.

## Producing the dump

For reference: the file on Google Drive was made with `./scripts/dump_db.sh`,
which is just `pg_dump --no-owner --no-privileges --clean --if-exists
--format=plain` against `$DATABASE_URL`, gzipped. Only relevant if you're
the one updating it — restoring just needs the file.

## Troubleshooting

**`psql: FATAL: Peer authentication failed for user "yart"`** — pass
`-h 127.0.0.1` to force TCP. Peer auth only applies on the unix socket.

**`uv sync` fails on `psycopg2-binary`** — `libpq-dev` and/or `python3-dev`
aren't installed.

**Frontend says "Load failed" on login/register** — almost always CORS.
Make sure the URL the browser is on (`localhost:5173` vs `127.0.0.1:5173`)
is listed in `CORS_ALLOWED_ORIGINS`. Restart the backend after editing
`.env`.

**Frontend hits the wrong API URL after I edited `frontend/.env`** —
Vite reads env files only at startup. Restart `npm run dev`.

**`pg_dump: server version mismatch`** — install `postgresql-client-17`
(use the same PGDG snippet from "System packages" above to get the
matching client).
