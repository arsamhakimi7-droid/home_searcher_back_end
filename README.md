# HomeFind Backend (FastAPI)

REST API for the HomeFind real-estate site: listings & search, favorites, agents, neighborhood guides,
mortgage tools, and JWT login. SQLite by default (Postgres-ready). Python 3.10+.

## Run

```bash
python -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1   (cmd: .venv\Scripts\activate.bat)
pip install -r requirements.txt
cp .env.example .env                 # Windows: copy .env.example .env   (optional for local dev)
uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000/api/...      Interactive docs: http://localhost:8000/docs
- Demo data is seeded on first start. Reset: `python -m app.seed --reset`
- Tests: `pytest -q` (26 tests)

## Configuration (`.env`)

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing key. **Set a long random value in production** (`python -c "import secrets; print(secrets.token_urlsafe(48))"`) |
| `CORS_ORIGINS` | Comma-separated frontend origins allowed to call the API (default `http://localhost:8443,http://localhost:5173`). **Add your deployed frontend URL.** |
| `DATABASE_URL` | Default `sqlite:///./homefind.db`. For Postgres: `postgresql+psycopg://user:pass@host/db` (and `pip install "psycopg[binary]"`) |
| `SEED_ON_STARTUP` | `true` loads demo data when the database is empty |
| `RATE_30Y_FIXED`, ... | Illustrative mortgage rates (%) |
| `FRONTEND_DIST` | Optional path to the frontend `dist/` to serve the site from this API too |

## Endpoints (all under `/api`)

| Area | Endpoints |
|---|---|
| Health | `GET /health` |
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Properties | `GET /properties` (q, listing_type, category, min_price, max_price, beds, baths, home_type, sort, page, page_size), `GET /properties/{id}`, `/properties/trending`, `/properties/recommended`, `/properties/categories`, `/properties/suggestions?q=` |
| Favorites (auth) | `GET /favorites`, `GET /favorites/ids`, `PUT /favorites/{id}`, `DELETE /favorites/{id}` |
| Agents | `GET /agents`, `GET /agents/{id}`, `POST /agents/{id}/contact` |
| Neighborhoods | `GET /neighborhoods?q=`, `GET /neighborhoods/{zip}` |
| Mortgage | `GET /mortgage/rates`, `POST /mortgage/calculate`, `/mortgage/affordability`, `/mortgage/pre-approval` |
| Misc | `POST /subscribe` |

Authenticated requests send `Authorization: Bearer <token>` (returned by login/register).

## Placeholders to replace before launch

- Listings, agents, neighborhood stats are demo data (`app/seed.py`). Property image paths such as `/assets/xxx.png` are resolved by the **frontend's** origin.
- Mortgage rates are illustrative; pre-approval is an estimate (28/36 DTI), not a lender decision.
- Contact Agent / pre-approval / subscribe store records in the database but do not send email yet.
