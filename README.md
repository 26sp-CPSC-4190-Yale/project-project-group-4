[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/D8kToVOh)

# YArt Match

A web app for browsing art from the Yale University Art Gallery and connecting with people who have similar taste.

You swipe through artworks — right to like, left to pass. As you go, the app builds a taste profile from things like the artwork's style, department, artist nationality, and time period. When two users have similar enough profiles, they get matched and can message each other.

---

## Features

- **Swipe to explore** — browse YUAG artworks one at a time; drag, use arrow keys, or A/D to like or pass. There's also an undo button if you change your mind
- **Flip cards** — tap a card to flip it and see the full metadata (artist, date, medium, department, etc.)
- **Taste profile** — see your top taste signals broken down by style, department, nationality, and century, plus a grid of everything you've liked
- **Art of the Day** — a daily personalized recommendation based on your taste history (falls back to popular artworks if you're new)
- **Taste-based matching** — cosine similarity over Bayesian-scored taste vectors; users need at least 20 swipes before they enter the matching pool
- **Match requests & messaging** — the app surfaces potential matches; you send a request, they accept or decline, and then you can chat
- **Notifications** — a badge that polls every 30 seconds for new matches and pending requests
- **User profiles** — bio, profile photo, and stats (likes, passes, like rate, join date); only visible to matched users

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 7 |
| Backend | Django 6, Django REST Framework |
| Database | PostgreSQL (app data) + read-only Yale LUX SQLite (artwork data) |
| Auth | Token-based (24-hour expiry, custom DRF class) |
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
│   └── tests.py            # Test suite
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
# create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# install dependencies
pip install -r requirements.txt    # pinned
pip install -e .                   # or via pyproject.toml with uv

# copy and fill in your env vars
cp .env.example .env

# run migrations
python manage.py migrate

# start the dev server
python manage.py runserver
```

The API will be at `http://127.0.0.1:8000`.

### Running the tests

```bash
# first run (creates the test DB)
python manage.py test gallery --verbosity=2

# subsequent runs (reuse test DB, faster)
python manage.py test gallery --verbosity=2 --keepdb
```

Tests cover auth, interactions, taste signals, matches, messaging, notifications, and profiles.

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

Every swipe updates your **taste signals**. Each artwork has a set of (facet, value) pairs — things like classifier, department, artist nationality, and century — and liking or passing on the artwork nudges the score for each of those pairs up or down.

Scores use Bayesian smoothing so a single swipe doesn't immediately dominate:

```
score = (likes + α) / (likes + passes + 2α)    where α = 2
```

This keeps scores near 0.5 early on and only pulls them toward 0 or 1 as more evidence accumulates.

**Match detection** runs in a background thread every 15 swipes (so it doesn't slow down the swipe API):

1. Skip anyone with fewer than 20 total swipes — not enough signal yet.
2. Build a taste vector for the current user.
3. Compute cosine similarity against every other eligible user.
4. Create a `Match` (status: `pending`) for any pair above 0.30 similarity.

**Art of the Day** works in two phases: first pull candidate artworks that match your top taste signals, then score and rank those candidates. A daily tiebreaker (MD5 of artwork ID + date) keeps the pick stable for 24 hours.

---

## Data Source

Artwork data comes from the [Yale University Art Gallery LUX database](https://lux.collections.yale.edu/). Images are served by the Yale media CDN:

```
https://media.collections.yale.edu/thumbnail/yuag/obj/{artwork_id}
```

The LUX models (`Artwork`, `Agent`, `Classifier`, etc.) are read-only unmanaged Django models — this app never writes to them.

