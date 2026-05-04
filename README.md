[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/D8kToVOh)

# YArt Match

A full-stack web app for discovering art from the Yale University Art Gallery — and meeting people who share your taste.

Swipe right on art you like, left on art you don't. The app builds a taste profile from each artwork's classifiers, departments, artist nationalities, and centuries. When two users' profiles are similar enough, they're matched and can message each other.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [How the Matching Algorithm Works](#how-the-matching-algorithm-works)
- [Data Source](#data-source)
- [Contributing](#contributing)

---

## Features

- **Swipe to explore** — browse Yale University Art Gallery artworks one at a time; swipe or use arrow keys / A–D to like or pass, with an undo for the last swipe
- **Flip cards** — tap a card to see the artwork's full metadata (artist, date, medium, department)
- **Taste profile** — top taste signals broken down by classifier, department, nationality, and century, plus a paginated view of everything you've liked
- **Art of the Day** — a personalized daily recommendation based on your accumulated taste signals
- **Taste-based matching** — cosine similarity over Bayesian-scored taste vectors; only users with enough swipe history are considered
- **Match requests & messaging** — send match requests, accept or decline incoming ones, and chat once matched
- **Notification badge** — polls every 30 seconds for new matches and pending requests
- **User profiles** — bio, profile photo (JPEG/PNG/WebP, max 2 MB), and stats (likes, passes, like rate, join date)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 7 |
| Backend | Django 6, Django REST Framework 3 |
| Database | PostgreSQL (app data) + read-only Yale LUX SQLite (artwork data) |
| Auth | DRF Token Authentication (24-hour expiry) |
| Package management | npm (frontend), uv / pyproject.toml (backend) |

---

## Project Structure

```
project-project-group-4/
├── frontend/
│   ├── src/
│   │   ├── pages/          # Route-level views (Gallery, TasteProfile, Messages, etc.)
│   │   ├── components/     # Shared structural components (Layout)
│   │   ├── context/        # AuthContext — global auth state
│   │   ├── hooks/          # useSwipe — touch/mouse swipe detection
│   │   └── lib/            # constants, shared utilities
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── gallery/                # Django app
│   ├── migrations/
│   ├── models.py           # Interaction, TasteSignal, Match, Message, UserProfile
│   ├── auth.py             # ExpiringTokenAuthentication (24-hour TTL)
│   ├── taste.py            # Taste signal extraction, Bayesian scoring, match engine
│   ├── views.py
│   ├── serializers.py
│   ├── urls.py
│   └── tests.py            # Full test suite (75 tests)
├── backend/                # Django project config
│   ├── settings.py
│   └── urls.py
├── manage.py
├── pyproject.toml
├── requirements.txt
└── .env.example
```

---

## Getting Started

### Prerequisites

- Python 3.13+
- Node.js 18+
- PostgreSQL

### Backend

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# Install dependencies (pick one)
pip install -r requirements.txt    # pinned versions
pip install -e .                   # or via pyproject.toml with uv/pip

# Set up environment variables
cp .env.example .env               # then edit .env with your values

# Apply migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000`.

### Running the test suite

```bash
# First run — creates the test database
python manage.py test gallery --verbosity=2

# Subsequent runs — reuse the existing test DB (faster)
python manage.py test gallery --verbosity=2 --keepdb
```

75 tests cover: auth (register, login, logout, token expiry, password change), interactions, taste signals, artwork endpoints, matches, messaging, notifications, and profile.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | Django secret key (required) |
| `DEBUG` | `False` | Set to `True` for local development |
| `DATABASE_URL` | — | PostgreSQL connection string (required) |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated allowed hostnames |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated allowed CORS origins |
| `TOKEN_EXPIRY_HOURS` | `24` | Hours before an auth token is invalidated |

To point the frontend at a backend running on a different host or port, create `frontend/.env`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

---

## API Reference

### Authentication

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/register/` | — | Create an account — returns an auth token |
| `POST` | `/api/auth/login/` | — | Sign in — returns an auth token |
| `POST` | `/api/auth/logout/` | Required | Revoke the current token |
| `POST` | `/api/auth/change-password/` | Required | Change password; old token is invalidated and a new one returned |

Auth tokens expire after **24 hours**. A `401` response with `code: "token_expired"` means the user must log in again to obtain a fresh token.

### Artworks & Interactions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/artworks/` | Fetch up to 20 random unseen artworks |
| `GET` | `/api/artwork/<id>/` | Artwork detail with interaction counts |
| `POST` | `/api/interactions/` | Record a like or pass |
| `DELETE` | `/api/interactions/<artwork_id>/` | Undo the last swipe on an artwork |

### Taste & Recommendations

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/taste/me/` | Top 20 taste signals across all facet types |
| `GET` | `/api/liked/` | Paginated list of liked artworks |
| `GET` | `/api/art-of-the-day/` | Personalized daily artwork recommendation |

### Profile

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/profile/stats/` | Like/pass counts and like rate |
| `GET`, `PATCH` | `/api/profile/me/` | Get or update bio and profile photo |
| `GET` | `/api/profile/photo/<user_id>/` | Retrieve a user's profile photo |

### Matching & Messaging

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/matches/` | All matches with similarity scores |
| `POST` | `/api/matches/<user_id>/action/` | `request`, `accept`, or `decline` a match |
| `GET` | `/api/matches/<user_id>/facets/` | Top shared taste facets with a match |
| `DELETE` | `/api/matches/<user_id>/` | Unmatch and delete the conversation |
| `GET`, `POST` | `/api/messages/<user_id>/` | Read or send messages |
| `GET` | `/api/notifications/` | Count of new matches and pending requests |

---

## How the Matching Algorithm Works

Every swipe updates the user's **taste signals** — one per (facet, value) pair extracted from the artwork:

- **Classifier** — e.g. Painting, Sculpture, Photograph
- **Department** — e.g. Prints and Drawings, Asian Art
- **Nationality** — the artist's nationality
- **Century** — derived from the artwork's date string

Each signal tracks a like count and a pass count. The score is computed with **Bayesian smoothing** to avoid extreme values when there's limited evidence:

```
score = (likes + α) / (likes + passes + 2α)    where α = 2
```

Scores range from 0 to 1, anchored near 0.5 until enough swipes accumulate.

**Match detection** runs in a background thread every 15 swipes:

1. Skip users with fewer than 20 total swipes (cold-start guard).
2. Build a taste vector for the current user over every (facet, value) pair they've encountered.
3. Compute **cosine similarity** against every other eligible user's vector.
4. Create a `Match` record (status: `pending`) for any pair whose similarity exceeds 0.30.

**Art of the Day** selects from unseen artworks that score highest against the user's taste signals, with a deterministic daily tiebreaker (MD5 of artwork ID + today's date) so the recommendation stays stable for 24 hours.

---

## Data Source

Artwork data comes from the [Yale University Art Gallery LUX database](https://lux.collections.yale.edu/). Images are served by the Yale media CDN:

```
https://media.collections.yale.edu/thumbnail/yuag/obj/{artwork_id}
```

The LUX models (`Artwork`, `Agent`, `Classifier`, etc.) are read-only unmanaged Django models — this app never writes to them.

---

## Contributing

1. Fork the repo and create a feature branch off `main`.
2. Run `npm run lint` before opening a frontend PR.
3. Keep API changes consistent with the existing DRF serializer/view patterns.
4. Open a pull request with a clear description of what changed and why.
