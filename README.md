[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/D8kToVOh)

# YArt Match

YArt Match is a web app for browsing artwork from the Yale University Art Gallery and meeting people whose taste in art looks similar to yours. The basic loop is the one you'd expect from a swiping app: an artwork comes up, you like it or pass on it, and the next one appears. The twist is that every swipe nudges a profile of what you tend to go for — what departments, classifications, artist nationalities, and time periods — and once that profile is detailed enough, the backend starts comparing you against other users and suggesting matches. Once two people accept a match they can chat.

The app was built around the Yale LUX collections data (a snapshot of the YUAG catalog), which we treat as a read-only data source.

## What it does

- **Swipe through artwork.** Drag the card, use the arrow keys, or A/D to like or pass. There's an undo button if you change your mind on the last card.
- **Flip the card.** Tap or click an artwork to flip it and read the full date and accession number.
- **Build a taste profile.** As you swipe, the app accumulates per-facet like/pass counts and shows you your top signals broken down by classifier, department, artist nationality, and century, alongside a grid of everything you've liked.
- **Art of the Day.** A daily personalized recommendation that surfaces something the recommender thinks fits your taste, with a little explanation of which facets drove the pick. Cold-start users get the most-liked artwork instead.
- **Match with other users.** Once two users have enough swipe history, the matching engine compares their taste vectors using cosine similarity. If you're above the threshold, a match is created. Either side can request, accept, or decline, and either side can later unmatch.
- **Message your matches.** Plain text conversations between accepted matches, with date separators and the usual UX details.
- **See a match's profile.** Bio, photo, stats, and a "common likes" view that surfaces artworks you both liked. Profiles are only visible to people you've actually matched with.
- **Notification badge.** The frontend polls every 30 seconds for new matches and pending requests so the nav bar stays current.

## Tech stack

The backend is Django 6 with Django REST Framework. The frontend is React 19 built with Vite 7. The application database is PostgreSQL; on top of that, the gallery app has a set of unmanaged Django models that map onto the Yale LUX SQLite schema for the artwork catalog — Django reads from those tables but never writes to them (these are migrated to PostgreSQL). Auth is token-based with a 24-hour expiry, implemented as a small subclass of DRF's `TokenAuthentication`.

Backend dependencies are managed with `uv` / `pyproject.toml`. Frontend dependencies are plain npm.

## Getting started

You'll need Python 3.13+, Node 18+, and a PostgreSQL instance.

For the backend, create a virtual environment, install the dependencies, copy `.env.example` to `.env` and fill in the values, run migrations, and start the dev server:

```bash
python -m venv venv
source venv/bin/activate
uv sync
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

The API then lives at `http://127.0.0.1:8000`.

For the frontend:

```bash
cd frontend
npm install
npm run dev
```

That serves the app at `http://localhost:5173`. If you want to point the frontend at a backend running somewhere else, drop a `frontend/.env` with `VITE_API_URL=http://your-backend-host`.

### Running the tests

The Django test suite lives in `gallery/tests.py` and covers auth, interactions, taste signal updates, matching, messaging, notifications, and profiles.

```bash
python manage.py test gallery --verbosity=2
python manage.py test gallery --verbosity=2 --keepdb   # faster on subsequent runs
```

## Environment variables

Copy `.env.example` to `.env` and fill in:

- `SECRET_KEY` — Django secret key (required).
- `DEBUG` — `True` for local dev, `False` in production.
- `DATABASE_URL` — PostgreSQL connection string (required).
- `ALLOWED_HOSTS` — comma-separated allowed hostnames. Defaults to `127.0.0.1,localhost`.
- `CORS_ALLOWED_ORIGINS` — comma-separated origins allowed to call the API. Defaults to `http://localhost:5173`.

Token expiry is hardcoded to 24 hours in `backend/settings.py` (the auth class also reads it from settings if you'd rather override it there).

## Project layout

The repo is split into a Django backend at the root and a React frontend under `frontend/`. The main pieces of the backend are:

- `backend/` — Django project config (`settings.py`, `urls.py`, WSGI/ASGI entrypoints).
- `gallery/models.py` — both the unmanaged LUX models (`Artwork`, `Agent`, `Classifier`, `Department`, `Nationality`, `Place`, and their join tables) and the managed app models (`Interaction`, `TasteSignal`, `Match`, `Message`, `UserProfile`).
- `gallery/auth.py` — `ExpiringTokenAuthentication`, the 24-hour-token wrapper around DRF's `TokenAuthentication`.
- `gallery/taste.py` — taste signal extraction, Bayesian scoring, the matching engine, and the Art-of-the-Day recommender.
- `gallery/views.py`, `gallery/serializers.py`, `gallery/urls.py` — the REST API surface.
- `gallery/tests.py` — the test suite.

On the frontend, `frontend/src/pages/` holds the route-level views (Gallery, TasteProfile, Messages, Conversation, Profile, MatchProfile, Login, Register), `frontend/src/components/` has shared structural components (`Layout`, `ErrorBoundary`), `frontend/src/context/AuthContext.jsx` carries the token and user state, `frontend/src/hooks/useSwipe.js` is the touch/mouse swipe-detection hook used by the gallery, and `frontend/src/lib/` holds shared constants and date/string formatters.

## API reference

All authenticated endpoints expect `Authorization: Token <token>`. A `401` with `code: "token_expired"` means the token has aged out and the user needs to log in again.

**Auth**

- `POST /api/auth/register/` — create an account, returns a token.
- `POST /api/auth/login/` — sign in, returns a token.
- `POST /api/auth/logout/` — revoke the current token. Auth required.
- `POST /api/auth/change-password/` — change password; the old token is invalidated and a fresh one is returned. Auth required.

**Artwork & interactions**

- `GET /api/artworks/` — fetch up to 20 random unseen artworks.
- `POST /api/interactions/` — record a like or pass.
- `DELETE /api/interactions/<artwork_id>/` — undo a previous swipe on an artwork.
- `GET /api/liked/` — paginated list of liked artworks.

**Taste & recommendations**

- `GET /api/taste/me/` — top 20 taste signals across all facet types.
- `GET /api/art-of-the-day/` — the personalized daily artwork plus an explanation of which facets drove the pick.

**Profile**

- `GET /api/profile/stats/` — like/pass counts and like rate.
- `GET`, `PATCH /api/profile/me/` — get or update the current user's bio and profile photo.
- `GET /api/profile/photo/<user_id>/` — fetch a user's profile photo bytes.

**Matching & messaging**

- `GET /api/matches/` — all matches with similarity scores and statuses.
- `POST /api/matches/<user_id>/action/` — `request`, `accept`, or `decline` a match.
- `GET /api/matches/<user_id>/facets/` — the top shared taste facets between you and a match.
- `GET /api/matches/<user_id>/profile/` — a match's bio/stats. Only available once you're matched.
- `GET /api/matches/<user_id>/common-likes/` — artworks both of you have liked.
- `DELETE /api/matches/<user_id>/` — unmatch and delete the conversation.
- `GET`, `POST /api/messages/<user_id>/` — read or send messages.
- `GET /api/notifications/` — counts of new matches and pending requests.

## How the matching works

Every artwork has a set of `(facet, value)` pairs derived from the LUX data: classifier, department, artist nationality, and century. When you like or pass on an artwork, every one of those pairs has its like-count or pass-count nudged for you, and the score for that signal is recomputed using a Bayesian-smoothed estimate:

```
score = (likes + alpha) / (likes + passes + 2*alpha)
```

The smoothing keeps a single early swipe from dominating — scores stay near 0.5 until enough evidence has accumulated to pull them toward 0 or 1.

The matching engine runs in a background thread once every 15 swipes, so the swipe API itself stays fast. It looks at the user's taste vector (filtered to facet values with at least 3 swipes of evidence), finds candidate users who share at least one facet value and have at least 20 total swipes themselves, then computes cosine similarity against each candidate. If the best candidate scores above 0.30, a `Match` row is created with status `pending`, unless they have previously been matched.

Art of the Day uses the same taste signals but in two phases. The first phase pulls up to a few hundred candidate artworks per facet using the user's strongest signals; the second phase scores those candidates against the full signal map and ranks them. A daily MD5 tiebreaker keyed on `artwork_id + today's date` keeps the top pick stable for 24 hours.

## Data source

Artwork data comes from the [Yale University Art Gallery LUX database](https://lux.collections.yale.edu/). The schema is exposed to Django through unmanaged models, so the app reads catalog data but never writes back to it. Images are served directly from the Yale media CDN at `https://media.collections.yale.edu/thumbnail/yuag/obj/{artwork_id}`.

## Third-party code, packages, and data

Most of this app is original work, but there's a fair amount of code, infrastructure, and data we did not write ourselves. Here is what was used and why.

### Backend (Python)

- **[Django](https://www.djangoproject.com/) 6.0.3** — web framework. Provides the ORM, URL routing, request/response cycle, the auth/user model, the migration system, and the management-command framework. It is the standard web framework for Python and the one the course recommended; building all of this on something lighter would have required reinventing the ORM, migrations, and admin tooling.
- **[Django REST Framework](https://www.django-rest-framework.org/) 3.16** — REST layer on top of Django. Used for serializers, view decorators, throttling, and the token authentication base class we extend in `gallery/auth.py`. DRF is the default REST library in the Django ecosystem; using it gave us a token system with one subclass and consistent JSON serialization across the API.
- **[`rest_framework.authtoken.Token`](https://www.django-rest-framework.org/api-guide/authentication/#tokenauthentication)** — DRF's built-in `Token` model and `TokenAuthentication` class. Our `ExpiringTokenAuthentication` subclasses it to add a 24-hour TTL rather than reimplementing token storage.
- **[django-cors-headers](https://github.com/adamchainz/django-cors-headers) 4.9** — CORS middleware. Needed because the React dev server runs on a different origin than the Django API. It is the canonical CORS solution for Django.
- **[dj-database-url](https://github.com/jazzband/dj-database-url) 3.1** — parses a single `DATABASE_URL` string into Django's `DATABASES` config. Convenient for keeping configuration in one env var, especially across local dev and hosted deployments.
- **[psycopg2-binary](https://www.psycopg.org/) 2.9** — the PostgreSQL driver for Django. Required to talk to Postgres at all.
- **[Pillow](https://python-pillow.org/) 12** — image library. Used by Django's `ImageField` machinery and for handling profile-photo uploads.
- **[python-dotenv](https://github.com/theskumar/python-dotenv) 1.2** — loads `.env` files into the environment at startup so we can keep secrets and per-environment config out of `settings.py`.
- **[gunicorn](https://gunicorn.org/) 25** — the WSGI server used in production deployments. It is the default Python production server and what hosting platforms expect.
- **Python standard library** — `hashlib`, `math`, `re`, `threading`, `datetime`, `collections`. Used in `gallery/taste.py` and `gallery/views.py` for date parsing, cosine similarity, the daily-pick MD5 tiebreaker, and the background match-check thread.

### Frontend (JavaScript)

The complete list of npm packages is in `frontend/package.json`. Nothing else is pulled in at runtime — there are no UI component libraries, animation libraries, routing libraries, or HTTP clients. The app uses the browser's built-in `fetch`, plain CSS in `App.css`, and a tiny custom routing scheme based on view state in `App.jsx`.

**Runtime dependencies**

- **[react](https://react.dev/) ^19.2.0** — the UI library. Everything in the UI (gallery card, swipe physics, taste profile, conversation view) is plain React with hooks.
- **[react-dom](https://react.dev/) ^19.2.0** — React's DOM renderer; mounts the app into `index.html`.

**Dev dependencies**

- **[vite](https://vitejs.dev/) ^7.3.1** — dev server and production bundler. Gave us fast HMR during development and a small, reasonable production build with no manual webpack config.
- **[@vitejs/plugin-react](https://www.npmjs.com/package/@vitejs/plugin-react) ^5.1.1** — official Vite plugin that wires up React Fast Refresh and JSX transform.
- **[eslint](https://eslint.org/) ^9.39.1** — linter for the React code.
- **[@eslint/js](https://www.npmjs.com/package/@eslint/js) ^9.39.1** — ESLint's recommended JavaScript rule set, used as the base config in `eslint.config.js`.
- **[eslint-plugin-react-hooks](https://www.npmjs.com/package/eslint-plugin-react-hooks) ^7.0.1** — enforces the rules of hooks.
- **[eslint-plugin-react-refresh](https://www.npmjs.com/package/eslint-plugin-react-refresh) ^0.4.24** — keeps components compatible with Vite's Fast Refresh.
- **[globals](https://www.npmjs.com/package/globals) ^16.5.0** — provides the standard set of global variable names (browser, node, etc.) for ESLint configs.
- **[@types/react](https://www.npmjs.com/package/@types/react) ^19.2.7** — TypeScript types for React; pulled in for editor IntelliSense even though the project itself is plain JavaScript.
- **[@types/react-dom](https://www.npmjs.com/package/@types/react-dom) ^19.2.3** — TypeScript types for `react-dom`, same reasoning.

esbuild and rollup ship transitively under Vite as the JS transformer and bundler respectively; they are not declared in `package.json` directly.

### Data and external services

- **[Yale University Art Gallery LUX](https://lux.collections.yale.edu/) data** — every artwork, artist, classification, department, nationality, and place in the app comes from the LUX collections data. The unmanaged models in `gallery/models.py` map directly to the LUX tables. The course handed this dataset to us as the expected source, and it is the authoritative public source for YUAG catalog data.
- **Yale media CDN** — artwork thumbnails are loaded from `https://media.collections.yale.edu/thumbnail/yuag/obj/{artwork_id}`. Hosting our own copies would have meant downloading and republishing thousands of high-resolution images we have no rights to redistribute.

Everything else — the swipe interaction, taste-signal model, matching engine, Art-of-the-Day recommender, messaging, profile system, the React UI, the CSS, the migrations — was written for this project.
